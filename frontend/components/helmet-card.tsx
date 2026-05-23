"use client"

import { Card, CardContent } from "@/components/ui/card"
import { HardHat, Thermometer, Volume2, Eye } from "lucide-react"
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
    label: "안전",
    bgGlow: "shadow-[0_0_20px_rgba(34,197,94,0.3)]",
    statusText: "이상 없음",
  },
  MID: {
    color: "bg-risk-medium",
    textColor: "text-risk-medium",
    borderColor: "border-risk-medium",
    label: "주의",
    bgGlow: "shadow-[0_0_20px_rgba(234,179,8,0.3)]",
    statusText: "위험 요소 감지",
  },
  HIGH: {
    color: "bg-risk-high",
    textColor: "text-risk-high",
    borderColor: "border-risk-high",
    label: "위험",
    bgGlow: "shadow-[0_0_20px_rgba(239,68,68,0.3)]",
    statusText: "즉시 확인 필요",
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
    <Card
      className={cn(
        "relative overflow-hidden transition-all duration-300 hover:scale-[1.02]",
        "border-2",
        config.borderColor,
        config.bgGlow
      )}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-12 w-12 items-center justify-center rounded-xl",
                config.color
              )}
            >
              <HardHat className="h-6 w-6 text-background" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Helmet {id}
              </h3>
              <p className="text-xs text-muted-foreground font-mono">
                {deviceId}
              </p>
            </div>
          </div>

          <div
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-bold",
              config.color,
              "text-background"
            )}
          >
            {config.label}
          </div>
        </div>

        <div
          className={cn(
            "flex items-center gap-2 mb-4 px-3 py-2 rounded-lg border",
            config.borderColor,
            "bg-secondary/50"
          )}
        >
          <Eye className={cn("h-4 w-4", config.textColor)} />
          <span className={cn("text-sm font-semibold", config.textColor)}>
            {helmetOn ? config.statusText : "안전모 미착용 감지"}
          </span>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-muted-foreground">위험도</span>
            <span className={cn("text-xs font-semibold", config.textColor)}>
              {riskLevel}
            </span>
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                config.color
              )}
              style={{ width: `${Math.max(8, Math.round(score * 100))}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="flex items-center gap-2 p-3 rounded-lg bg-secondary">
            <Thermometer className="h-4 w-4 text-risk-high" />
            <div>
              <p className="text-xs text-muted-foreground">온도</p>
              <p className="text-sm font-semibold">{temperature}°C</p>
            </div>
          </div>

          <div className="flex items-center gap-2 p-3 rounded-lg bg-secondary">
            <Volume2 className="h-4 w-4 text-risk-medium" />
            <div>
              <p className="text-xs text-muted-foreground">소음</p>
              <p className="text-sm font-semibold">{noise} dB</p>
            </div>
          </div>
        </div>

        <div className="pt-3 border-t border-border" />
        <p className="text-[10px] text-muted-foreground text-right mt-2">
          {lastUpdate}
        </p>
      </CardContent>
    </Card>
  )
}
