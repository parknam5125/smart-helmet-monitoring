"use client"

import { Card, CardContent } from "@/components/ui/card"
import { HardHat, Thermometer, Volume2, ShieldCheck } from "lucide-react"
import { cn } from "@/lib/utils"

export type RiskLevel = "LOW" | "MID" | "HIGH"

interface HelmetCardProps {
  id: number
  deviceId: string
  helmetOn: boolean
  riskLevel: RiskLevel
  temperature: number
  noise: number
  score: number
  lastUpdate: string
}

const riskConfig = {
  LOW: {
    color: "bg-risk-low",
    textColor: "text-risk-low",
    borderColor: "border-risk-low",
    label: "Safe",
    statusText: "Helmet detected",
  },
  MID: {
    color: "bg-risk-medium",
    textColor: "text-risk-medium",
    borderColor: "border-risk-medium",
    label: "Warning",
    statusText: "Check worker status",
  },
  HIGH: {
    color: "bg-risk-high",
    textColor: "text-risk-high",
    borderColor: "border-risk-high",
    label: "Danger",
    statusText: "Immediate check required",
  },
}

export function HelmetCard({
  id,
  deviceId,
  helmetOn,
  riskLevel,
  temperature,
  noise,
  score,
  lastUpdate,
}: HelmetCardProps) {
  const config = riskConfig[riskLevel]

  return (
    <Card className={cn("border-2 transition-colors", config.borderColor)}>
      <CardContent className="p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className={cn(
                "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg",
                config.color
              )}
            >
              <HardHat className="h-6 w-6 text-background" />
            </div>
            <div className="min-w-0">
              <h3 className="truncate text-base font-semibold text-foreground">
                Helmet {id}
              </h3>
              <p className="truncate font-mono text-xs text-muted-foreground">
                {deviceId}
              </p>
            </div>
          </div>

          <div
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-bold text-background",
              config.color
            )}
          >
            {config.label}
          </div>
        </div>

        <div
          className={cn(
            "mb-4 flex items-center gap-2 rounded-lg border px-3 py-2",
            config.borderColor,
            "bg-secondary/50"
          )}
        >
          <ShieldCheck className={cn("h-4 w-4", config.textColor)} />
          <span className={cn("text-sm font-semibold", config.textColor)}>
            {helmetOn ? "헬멧 이상 없음" : "헬멧 미착용자 발견"}
          </span>
        </div>

        <div className="mb-4">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Risk score</span>
            <span className={cn("text-xs font-semibold", config.textColor)}>
              {Math.round(score * 100)}%
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-secondary">
            <div
              className={cn("h-full rounded-full transition-all", config.color)}
              style={{ width: `${Math.max(8, Math.round(score * 100))}%` }}
            />
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2 rounded-lg bg-secondary p-3">
            <Thermometer className="h-4 w-4 text-risk-high" />
            <div>
              <p className="text-xs text-muted-foreground">Temp</p>
              <p className="text-sm font-semibold">{temperature} C</p>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-lg bg-secondary p-3">
            <Volume2 className="h-4 w-4 text-risk-medium" />
            <div>
              <p className="text-xs text-muted-foreground">Noise</p>
              <p className="text-sm font-semibold">{noise} dB</p>
            </div>
          </div>
        </div>

        <div className="border-t border-border pt-3 text-right text-[10px] text-muted-foreground">
          Updated {lastUpdate}
        </div>
      </CardContent>
    </Card>
  )
}
