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

const TTS_LABEL: Record<string, string> = {
  ready: "suara siap",
  pending: "suara diproses",
  failed: "suara gagal",
};

const formatDateTime = (iso: string | null | undefined): string => {
  if (!iso) return "—";
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

const outcomeText = (reminder: ReminderOut): string => {
  const at = formatDateTime(reminder.remind_at);
  switch (reminder.status) {
    case "sent":
      return `Terkirim ke perangkat sekitar ${at}`;
    case "failed":
      return `Gagal terkirim sekitar ${at}`;
    case "cancelled":
      return "Dibatalkan sebelum jatuh tempo";
    default:
      return `Akan diingatkan ${at} (${relativeAt(reminder.remind_at)})`;
  }
};

interface HistoryRowProps {
  label: string;
  value: string;
  tone?: "default" | "danger" | "success";
}

function HistoryRow({ label, value, tone = "default" }: HistoryRowProps) {
  const valueClass =
    tone === "danger"
      ? "text-bmo-red"
      : tone === "success"
        ? "text-emerald-700"
        : "text-slate-600";
  return (
    <div className="flex items-start gap-2">
      <span className="w-20 shrink-0 text-slate-400">{label}</span>
      <span className={`min-w-0 flex-1 break-words ${valueClass}`}>
        {value}
      </span>
    </div>
  );
}

export function ReminderCard({
  reminder,
  onCancel,
  cancelling,
}: ReminderCardProps) {
  const tone = STATUS_TONE[reminder.status] ?? "info";
  const label = STATUS_LABEL[reminder.status] ?? reminder.status;
  const cancellable = reminder.status === "scheduled";

  const outcomeTone: "default" | "danger" | "success" =
    reminder.status === "failed"
      ? "danger"
      : reminder.status === "sent"
        ? "success"
        : "default";

  return (
    <div className="flex items-start gap-3 rounded-lg border border-bmo-border bg-surface-elev p-4">
      <BmoMascot size={48} />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-medium text-bmo-dark">
            {reminder.title}
          </p>
          <BmoBadge tone={tone}>{label}</BmoBadge>
          {reminder.task_id ? <BmoBadge tone="info">task</BmoBadge> : null}
        </div>

        <div className="rounded-md border border-bmo-border/60 bg-white/40 p-2.5">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Riwayat
          </p>
          <div className="space-y-1 text-xs">
            <HistoryRow
              label="Dibuat"
              value={formatDateTime(reminder.created_at)}
            />
            <HistoryRow
              label="Jadwal"
              value={`${formatDateTime(reminder.remind_at)} (${relativeAt(
                reminder.remind_at,
              )})`}
            />
            <HistoryRow
              label="Status"
              value={outcomeText(reminder)}
              tone={outcomeTone}
            />
            <HistoryRow label="Channel" value={reminder.channel} />
            {reminder.tts_status ? (
              <HistoryRow
                label="Suara"
                value={TTS_LABEL[reminder.tts_status] ?? reminder.tts_status}
                tone={reminder.tts_status === "failed" ? "danger" : "default"}
              />
            ) : null}
            {reminder.failure_reason ? (
              <HistoryRow
                label="Alasan"
                value={reminder.failure_reason}
                tone="danger"
              />
            ) : null}
          </div>
        </div>

        {cancellable ? (
          <div className="pt-0.5">
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
