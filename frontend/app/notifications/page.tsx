"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/reports-client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import Link from "next/link";

export default function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data: notifData, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => listNotifications(),
    refetchInterval: 30_000,
  });

  const { data: unread } = useQuery({
    queryKey: ["notifications-unread"],
    queryFn: getUnreadCount,
    refetchInterval: 30_000,
  });

  const markReadMut = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });

  const markAllReadMut = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
      toast.success(`${data.marked_read} notifications marked read`);
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notifications</h1>
          <p className="text-muted-foreground">
            {unread?.count ? `${unread.count} unread` : "No unread notifications"}
          </p>
        </div>
        {unread && unread.count > 0 && (
          <Button variant="outline" onClick={() => markAllReadMut.mutate()}>
            Mark All Read
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : notifData && notifData.items.length > 0 ? (
        <div className="space-y-2">
          {notifData.items.map((n) => (
            <Card
              key={n.id}
              className={`transition-colors ${!n.is_read ? "border-primary/20 bg-primary/5" : ""}`}
            >
              <CardContent className="flex items-start justify-between p-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {!n.is_read && <div className="h-2 w-2 rounded-full bg-primary" />}
                    <span className="font-medium">{n.title}</span>
                    <Badge variant="outline" className="text-[10px]">
                      {n.notification_type.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  {n.body && <p className="mt-1 text-sm text-muted-foreground">{n.body}</p>}
                  <p className="mt-1 text-xs text-muted-foreground">
                    {n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                  </p>
                  {n.link && (
                    <Link href={n.link} className="mt-1 text-xs text-primary hover:underline">
                      View details
                    </Link>
                  )}
                </div>
                {!n.is_read && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={() => markReadMut.mutate(n.id)}
                  >
                    Mark Read
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No notifications yet.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
