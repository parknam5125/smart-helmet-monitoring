"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, HardHat, ThermometerSun } from "lucide-react"
import { DashboardHeader } from "@/components/dashboard-header"
import { HelmetCard, type RiskLevel } from "@/components/helmet-card"
import { RiskSummary } from "@/components/risk-summary"
import { StatsCard } from "@/components/stats-card"

export interface HelmetData {
  id: number
  deviceId: string
  helmetOn: boolean
  riskLevel: RiskLevel
  temperature: number
  noise: number
  score: number
  lastUpdate: string
}

interface ParsedMonitoringEvent {
  deviceId: string
  helmetOn: boolean
  riskLevel: RiskLevel
  temperature: number | null
  noise: number | null
  score: number
}

interface DeviceStatusEvent {
  type: "device_status"
  device_id: string
  connected: boolean
  timestamp?: string
}

const DEMO_DEVICE_IDS = ["DEMO-1001", "DEMO-1002", "DEMO-1003"]

const riskMap: Record<string, RiskLevel> = {
  SAFE: "LOW",
  WARNING: "MID",
  DANGER: "HIGH",
  LOW: "LOW",
  MID: "MID",
  MEDIUM: "MID",
  HIGH: "HIGH",
}

const toNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value
  }

  if (typeof value === "string") {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }

  return null
}

const toRecord = (value: unknown): Record<string, unknown> => {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : {}
}

const parseMaybeJson = (value: unknown): unknown => {
  if (typeof value !== "string") {
    return value
  }

  try {
    return JSON.parse(value)
  } catch {
    return value
  }
}

const apiOrigin = (): string => {
  if (process.env.NEXT_PUBLIC_API_ORIGIN) {
    return process.env.NEXT_PUBLIC_API_ORIGIN
  }

  const host =
    typeof window !== "undefined" && window.location.hostname
      ? window.location.hostname
      : "localhost"

  return `http://${host}:8000`
}

const wsUrl = (): string => {
  return apiOrigin().replace(/^http/, "ws") + "/ws/monitoring"
}

const makeDemoHelmet = (index: number): HelmetData => {
  const wave = Math.sin(Date.now() / 4000 + index)
  const profiles: Array<{
    riskLevel: RiskLevel
    baseTemp: number
    baseNoise: number
    helmetOn: boolean
    score: number
  }> = [
    {
      riskLevel: "LOW",
      baseTemp: 24.5,
      baseNoise: 63,
      helmetOn: true,
      score: 0.28,
    },
    {
      riskLevel: "MID",
      baseTemp: 31.5,
      baseNoise: 82,
      helmetOn: true,
      score: 0.62,
    },
    {
      riskLevel: "HIGH",
      baseTemp: 35.8,
      baseNoise: 94,
      helmetOn: false,
      score: 0.92,
    },
  ]
  const profile = profiles[index]

  return {
    id: index + 2,
    deviceId: DEMO_DEVICE_IDS[index],
    helmetOn: profile.helmetOn,
    riskLevel: profile.riskLevel,
    temperature: Math.round((profile.baseTemp + wave * 0.8) * 10) / 10,
    noise: Math.round(profile.baseNoise + wave * 3),
    score: profile.score,
    lastUpdate: new Date().toLocaleTimeString("ko-KR"),
  }
}

const normalizeBackendEvent = (value: unknown): ParsedMonitoringEvent | null => {
  const root = toRecord(value)
  const payload = toRecord(parseMaybeJson(root.payload ?? root.raw_payload ?? root))
  const assessment = toRecord(
    parseMaybeJson(root.assessment ?? root.raw_assessment ?? root)
  )
  const sensor = toRecord(payload.sensor ?? root.sensor)
  const detection = toRecord(payload.detection ?? root.detection)

  const temperature = toNumber(
    sensor.temperature_c ??
      sensor.temperature ??
      payload.temperature_c ??
      root.temperature_c
  )
  const noise = toNumber(
    sensor.noise_db ?? sensor.noise ?? payload.noise_db ?? root.noise_db
  )

  const rawRisk = String(
    assessment.risk_level ??
      assessment.riskLevel ??
      root.risk_level ??
      root.riskLevel ??
      "SAFE"
  ).toUpperCase()
  const noHelmetCount =
    toNumber(detection.no_helmet_count ?? root.no_helmet_count) ?? 0
  const helmetCount =
    toNumber(detection.helmet_count ?? root.helmet_count) ?? 0
  const helmetDetected = Boolean(
    detection.helmet_detected ?? root.helmet_detected ?? helmetCount > 0
  )
  const riskScore = toNumber(assessment.risk_score ?? root.risk_score) ?? 0

  return {
    deviceId: String(payload.device_id ?? root.device_id ?? "helmet-pi-01"),
    helmetOn: helmetDetected && noHelmetCount === 0,
    riskLevel: riskMap[rawRisk] ?? "LOW",
    temperature,
    noise,
    score: Math.max(0.08, Math.min(1, riskScore / 100)),
  }
}

export default function DashboardPage() {
  const [helmets, setHelmets] = useState<HelmetData[]>([])
  const [lastRefresh, setLastRefresh] = useState("")
  const [mounted, setMounted] = useState(false)
  const [serverConnected, setServerConnected] = useState(false)
  const [piConnected, setPiConnected] = useState(false)
  const [piDeviceId, setPiDeviceId] = useState<string | null>(null)

  const refreshDemoHelmets = useCallback(() => {
    const demoHelmets = DEMO_DEVICE_IDS.map((_, index) => makeDemoHelmet(index))

    setHelmets((prev) => {
      const realHelmets = prev.filter(
        (helmet) => !DEMO_DEVICE_IDS.includes(helmet.deviceId)
      )

      return [...realHelmets, ...demoHelmets]
    })
  }, [])

  const upsertHelmet = useCallback((event: ParsedMonitoringEvent) => {
    const now = new Date()

    setHelmets((prev) => {
      const existing = prev.find((item) => item.deviceId === event.deviceId)
      const nextHelmet: HelmetData = {
        id: existing?.id ?? 1,
        deviceId: event.deviceId,
        helmetOn: event.helmetOn,
        riskLevel: event.riskLevel,
        temperature:
          event.temperature !== null
            ? Math.round(event.temperature * 10) / 10
            : (existing?.temperature ?? 0),
        noise:
          event.noise !== null
            ? Math.round(event.noise)
            : (existing?.noise ?? 0),
        score: event.score,
        lastUpdate: now.toLocaleTimeString("ko-KR"),
      }

      return [
        nextHelmet,
        ...prev.filter((item) => item.deviceId !== event.deviceId),
      ]
    })

    setLastRefresh(now.toLocaleTimeString("ko-KR"))
  }, [])

  const fetchLatest = useCallback(async () => {
    try {
      const response = await fetch(`${apiOrigin()}/api/latest`, {
        cache: "no-store",
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      const devices = Array.isArray(data?.devices) ? data.devices : [data]

      devices
        .map(normalizeBackendEvent)
        .filter((item): item is ParsedMonitoringEvent => item !== null)
        .forEach((item) => {
          setPiConnected(true)
          setPiDeviceId(item.deviceId)
          upsertHelmet(item)
        })

      setServerConnected(true)
    } catch (error) {
      console.error("Failed to fetch latest monitoring data", error)
      setServerConnected(false)
    }
  }, [upsertHelmet])

  useEffect(() => {
    setMounted(true)
    refreshDemoHelmets()
    fetchLatest()

    const timer = setInterval(() => {
      refreshDemoHelmets()
    }, 1000)

    return () => clearInterval(timer)
  }, [fetchLatest, refreshDemoHelmets])

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let closedByEffect = false

    const connect = () => {
      socket = new WebSocket(wsUrl())

      socket.onopen = () => {
        setServerConnected(true)
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data?.type === "device_status") {
            const status = data as DeviceStatusEvent
            setPiConnected(Boolean(status.connected))
            setPiDeviceId(status.device_id)
            return
          }

          const parsed = normalizeBackendEvent(data)
          if (parsed) {
            setPiConnected(true)
            setPiDeviceId(parsed.deviceId)
            upsertHelmet(parsed)
          }
        } catch (error) {
          console.error("Failed to parse monitoring WebSocket message", error)
        }
      }

      socket.onclose = () => {
        setServerConnected(false)
        if (!closedByEffect) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    connect()

    return () => {
      closedByEffect = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
      }
      socket?.close()
    }
  }, [upsertHelmet])

  const highRiskCount = helmets.filter((h) => h.riskLevel === "HIGH").length
  const avgTemperature =
    helmets.length > 0
      ? helmets.reduce((sum, h) => sum + h.temperature, 0) / helmets.length
      : 0

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto p-4 sm:p-6 lg:p-8">
        <DashboardHeader
          onRefresh={fetchLatest}
          serverConnected={serverConnected}
          piConnected={piConnected}
          piDeviceId={piDeviceId}
        />

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <StatsCard title="Devices" value={helmets.length} icon={HardHat} />
          <StatsCard title="High Risk" value={highRiskCount} icon={AlertTriangle} />
          <StatsCard
            title="Avg Temp"
            value={`${avgTemperature.toFixed(1)} C`}
            icon={ThermometerSun}
          />
        </div>

        <div className="mt-6">
          <RiskSummary helmets={helmets} />
        </div>

        <div className="mt-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Helmet Status</h2>
            <span className="text-xs text-muted-foreground">
              Last update: {mounted && lastRefresh ? lastRefresh : "waiting"}
            </span>
          </div>

          {helmets.length === 0 ? (
            <div className="w-full rounded-lg border py-20 text-center text-muted-foreground">
              Waiting for Raspberry Pi data
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {helmets.map((helmet) => (
                <HelmetCard key={helmet.deviceId} {...helmet} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
