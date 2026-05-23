"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { HardHat, RefreshCw, Settings } from "lucide-react"
import { useState } from "react"

interface DashboardHeaderProps {
  onRefresh?: () => void
  isConnected?: boolean
}

export function DashboardHeader({
  onRefresh,
  isConnected = false,
}: DashboardHeaderProps) {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = () => {
    setIsRefreshing(true)
    onRefresh?.()
    setTimeout(() => setIsRefreshing(false), 1000)
  }

  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
          <HardHat className="h-6 w-6 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground sm:text-2xl">
            스마트 안전모 모니터링
          </h1>
          <p className="text-sm text-muted-foreground">
            실시간 작업자 안전 현황
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Badge
          variant="outline"
          className={
            isConnected
              ? "bg-risk-low/10 text-risk-low border-risk-low"
              : "bg-muted text-muted-foreground border-muted-foreground/30"
          }
        >
          <span
            className={`mr-1.5 h-2 w-2 rounded-full ${
              isConnected ? "bg-risk-low animate-pulse" : "bg-muted-foreground"
            }`}
          />
          {isConnected ? "실시간 연결됨" : "서버 연결 대기 중"}
        </Badge>
        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw
            className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
          />
        </Button>
        <Button variant="outline" size="icon">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
