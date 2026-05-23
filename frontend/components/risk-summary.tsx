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
  const safetyRate = total > 0 ? ((lowCount / total) * 100).toFixed(0) : "0"

  const riskData = [
    {
      level: "LOW" as const,
      label: "안전",
      count: lowCount,
      color: "bg-risk-low",
      textColor: "text-risk-low",
    },
    {
      level: "MID" as const,
      label: "주의",
      count: midCount,
      color: "bg-risk-medium",
      textColor: "text-risk-medium",
    },
    {
      level: "HIGH" as const,
      label: "위험",
      count: highCount,
      color: "bg-risk-high",
      textColor: "text-risk-high",
    },
  ]

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">위험도 현황</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 mb-4">
          {riskData.map((risk) => (
            <div key={risk.level} className="flex-1 text-center">
              <div className={cn("text-3xl font-bold mb-1", risk.textColor)}>
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
        <div className="h-3 bg-secondary rounded-full overflow-hidden flex">
          {riskData.map((risk) => (
            <div
              key={risk.level}
              className={cn("h-full transition-all duration-500", risk.color)}
              style={{
                width: `${total > 0 ? (risk.count / total) * 100 : 0}%`,
              }}
            />
          ))}
        </div>
        <div className="flex justify-between mt-2 text-xs text-muted-foreground">
          <span>전체 {total}명</span>
          <span>
            안전율{" "}
            <span className="text-risk-low font-semibold">{safetyRate}%</span>
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
