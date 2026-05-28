import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { isReady } from "../lib/env";
import { ReminderOut } from "../lib/types";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { BmoButton } from "../components/bmo/BmoButton";
import { ReminderCard } from "../components/reminders/ReminderCard";

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "Semua" },
  { value: "scheduled", label: "Dijadwalkan" },
  { value: "sent", label: "Terkirim" },
  { value: "failed", label: "Gagal" },
  { value: "cancelled", label: "Dibatalkan" },
];

export function RemindersPage() {
  const ready = isReady();
  const userId = ready.ok ? ready.userId : null;

  const [reminders, setReminders] = useState<ReminderOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async (uid: string, status: string) => {
    setLoading(true);
    setError(null);
    try {
      setReminders(await api.getReminders(uid, status || undefined));
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) void load(userId, filter);
  }, [userId, filter]);

  const handleCancel = async (reminderId: string) => {
    setBusyId(reminderId);
    try {
      await api.cancelReminder(reminderId);
      if (userId) await load(userId, filter);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-medium text-bmo-dark">Pengingat</h1>
          <p className="text-sm text-slate-500">
            Daftar reminder yang akan diputar BMO sebagai suara saat jatuh tempo.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="flex flex-wrap gap-1 rounded-md border border-bmo-border bg-surface-elev p-1">
            {STATUS_OPTIONS.map((opt) => {
              const active = filter === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFilter(opt.value)}
                  disabled={!userId || loading}
                  className={`cursor-pointer rounded px-3 py-1 text-xs font-medium transition-colors ${
                    active
                      ? "bg-bmo-dark text-bmo-screen"
                      : "text-slate-600 hover:bg-bmo-screen/40"
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
          <BmoButton
            variant="secondary"
            size="sm"
            onClick={() => userId && load(userId, filter)}
            disabled={!userId || loading}
          >
            Refresh
          </BmoButton>
        </div>
      </header>

      {loading ? <LoadingState /> : null}
      {error ? (
        <ErrorState
          error={error}
          onRetry={() => userId && load(userId, filter)}
        />
      ) : null}
      {!loading && !error ? (
        reminders.length === 0 ? (
          <EmptyState
            face="idle"
            title="Belum ada pengingat"
            description="Buat tugas dengan deadline atau katakan 'ingatkan ada tugas' ke BMO untuk menjadwalkan pengingat."
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {reminders.map((r) => (
              <ReminderCard
                key={r.id}
                reminder={r}
                onCancel={handleCancel}
                cancelling={busyId === r.id}
              />
            ))}
          </div>
        )
      ) : null}
    </section>
  );
}
