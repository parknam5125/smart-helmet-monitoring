"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { RiskLevel } from "./helmet-card"

interface RiskSummaryProps {
  helmets: { riskLevel: RiskLevel }[]
}

export function RiskSummary({ helmets }: RiskSummaryProps) {
  const lowCount = helmets.filter((h) => h.riskLevel === "LOW").length
  const midCount = helmets.filter((h) => h.riskLevel === "MID").length
  const highCount = helmets.filter((h) => h.riskLevel === "HIGH").length
  const total = helmets.length
  const safetyRate = total > 0 ? Math.round((lowCount / total) * 100) : 0

  const riskData = [
    {
      level: "LOW" as const,
      label: "Safe",
      count: lowCount,
      color: "bg-risk-low",
      textColor: "text-risk-low",
    },
    {
      level: "MID" as const,
      label: "Warning",
      count: midCount,
      color: "bg-risk-medium",
      textColor: "text-risk-medium",
    },
    {
      level: "HIGH" as const,
      label: "Danger",
      count: highCount,
      color: "bg-risk-high",
      textColor: "text-risk-high",
    },
  ]

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Risk Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center gap-4">
          {riskData.map((risk) => (
            <div key={risk.level} className="flex-1 text-center">
              <div className={cn("mb-1 text-3xl font-bold", risk.textColor)}>
                {risk.count}
              </div>
              <div className="flex items-center justify-center gap-1.5">
                <div className={cn("h-2 w-2 rounded-full", risk.color)} />
                <span className="text-xs text-muted-foreground">
                  {risk.label}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex h-3 overflow-hidden rounded-full bg-secondary">
          {riskData.map((risk) => (
            <div
              key={risk.level}
              className={cn("h-full transition-all", risk.color)}
              style={{
                width: `${total > 0 ? (risk.count / total) * 100 : 0}%`,
              }}
            />
          ))}
        </div>
        <div className="mt-2 flex justify-between text-xs text-muted-foreground">
          <span>Total {total}</span>
          <span>
            Safe rate{" "}
            <span className="font-semibold text-risk-low">{safetyRate}%</span>
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
