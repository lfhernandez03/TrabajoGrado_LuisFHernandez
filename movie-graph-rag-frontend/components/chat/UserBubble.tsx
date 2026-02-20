"use client";

import { User } from "lucide-react";
import type { ChatMessage } from "@/services/chat.service";

interface UserBubbleProps {
  message: ChatMessage;
}

export function UserBubble({ message }: UserBubbleProps) {
  return (
    <div className="flex justify-end gap-3">
      <div className="max-w-[80%]">
        <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className="text-[10px] text-muted-foreground text-right mt-1 mr-1">
          {new Date(message.timestamp).toLocaleTimeString("es-ES", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
      <div className="shrink-0 h-8 w-8 bg-primary/20 rounded-full flex items-center justify-center">
        <User className="h-4 w-4 text-primary" />
      </div>
    </div>
  );
}
