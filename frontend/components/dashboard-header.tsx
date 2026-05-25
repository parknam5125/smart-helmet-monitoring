"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { HardHat, RefreshCw } from "lucide-react"
import { useState } from "react"

interface DashboardHeaderProps {
  onRefresh?: () => void
  serverConnected?: boolean
  piConnected?: boolean
  piDeviceId?: string | null
}

export function DashboardHeader({
  onRefresh,
  serverConnected = false,
  piConnected = false,
  piDeviceId,
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
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary">
          <HardHat className="h-6 w-6 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground sm:text-2xl">
            Smart Helmet Monitoring
          </h1>
          <p className="text-sm text-muted-foreground">
            Raspberry Pi camera telemetry and server-side helmet detection
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Badge
          variant="outline"
          className={
            serverConnected
              ? "border-risk-low bg-risk-low/10 text-risk-low"
              : "border-muted-foreground/30 bg-muted text-muted-foreground"
          }
        >
          <span
            className={`mr-1.5 h-2 w-2 rounded-full ${
              serverConnected ? "bg-risk-low" : "bg-muted-foreground"
            }`}
          />
          {serverConnected ? "Server connected" : "Server waiting"}
        </Badge>

        <Badge
          variant="outline"
          className={
            piConnected
              ? "border-risk-low bg-risk-low/10 text-risk-low"
              : "border-risk-medium/60 bg-risk-medium/10 text-risk-medium"
          }
        >
          <span
            className={`mr-1.5 h-2 w-2 rounded-full ${
              piConnected ? "animate-pulse bg-risk-low" : "bg-risk-medium"
            }`}
          />
          {piConnected
            ? `Pi connected${piDeviceId ? `: ${piDeviceId}` : ""}`
            : "Pi waiting"}
        </Badge>

        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
          disabled={isRefreshing}
          aria-label="Refresh"
        >
          <RefreshCw
            className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
          />
        </Button>
      </div>
    </header>
  )
}
