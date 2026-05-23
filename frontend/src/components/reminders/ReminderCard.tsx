import { ReminderOut } from "../../lib/types";
import { parseIsoUtc } from "../../lib/format";
import { BmoMascot } from "../bmo/BmoMascot";
import { BmoBadge } from "../bmo/BmoBadge";
import { BmoButton } from "../bmo/BmoButton";

interface ReminderCardProps {
  reminder: ReminderOut;
  onCancel: (reminderId: string) => void;
  cancelling: boolean;
}

const STATUS_LABEL: Record<string, string> = {
  scheduled: "dijadwalkan",
  sent: "terkirim",
  failed: "gagal",
  cancelled: "dibatalkan",
};

const STATUS_TONE: Record<string, "online" | "offline" | "info"> = {
  scheduled: "info",
  sent: "online",
  failed: "offline",
  cancelled: "offline",
};

const formatRemindAt = (iso: string): string => {
  const d = parseIsoUtc(iso);
  if (!d) return iso;
  return d.toLocaleString("id-ID", {
    hour12: false,
    timeZone: "Asia/Jakarta",
    dateStyle: "medium",
    timeStyle: "short",
  });
};

const relativeAt = (iso: string): string => {
  const d = parseIsoUtc(iso);
  if (!d) return "";
  const diff = d.getTime() - Date.now();
  const abs = Math.abs(diff);
  const sign = diff < 0 ? "lalu" : "lagi";
  if (abs < 60_000) return diff < 0 ? "baru saja" : "sebentar lagi";
  if (abs < 3600_000) return `${Math.floor(abs / 60_000)} menit ${sign}`;
  if (abs < 86400_000) return `${Math.floor(abs / 3600_000)} jam ${sign}`;
  return `${Math.floor(abs / 86400_000)} hari ${sign}`;
};

export function ReminderCard({
  reminder,
  onCancel,
  cancelling,
}: ReminderCardProps) {
  const tone = STATUS_TONE[reminder.status] ?? "info";
  const label = STATUS_LABEL[reminder.status] ?? reminder.status;
  const cancellable = reminder.status === "scheduled";

  return (
    <div className="flex items-start gap-3 rounded-lg border border-bmo-border bg-surface-elev p-4">
      <BmoMascot size={48} />
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-medium text-bmo-dark">
            {reminder.title}
          </p>
          <BmoBadge tone={tone}>{label}</BmoBadge>
          {reminder.task_id ? (
            <BmoBadge tone="info">task</BmoBadge>
          ) : null}
        </div>
        <p className="text-xs text-slate-600">
          {formatRemindAt(reminder.remind_at)}
          <span className="ml-1 text-slate-400">
            ({relativeAt(reminder.remind_at)})
          </span>
        </p>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
          <span>channel {reminder.channel}</span>
          {reminder.tts_status ? (
            <span>tts {reminder.tts_status}</span>
          ) : null}
        </div>
        {reminder.failure_reason ? (
          <p className="break-words text-xs text-bmo-red">
            {reminder.failure_reason}
          </p>
        ) : null}
        {cancellable ? (
          <div className="pt-1">
            <BmoButton
              variant="secondary"
              size="sm"
              onClick={() => onCancel(reminder.id)}
              disabled={cancelling}
            >
              {cancelling ? "Membatalkan…" : "Batalkan"}
            </BmoButton>
          </div>
        ) : null}
      </div>
    </div>
  );
}
