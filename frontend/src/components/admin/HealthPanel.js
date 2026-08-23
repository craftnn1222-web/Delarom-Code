import React, { useEffect, useState, useCallback, useRef } from 'react';
import api from '../../utils/api';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import {
  Activity, Database, Image as ImageIcon, ShieldCheck, AlertTriangle,
  RefreshCw, CheckCircle2, XCircle, Server,
} from 'lucide-react';

const STATUS_STYLES = {
  ok: { color: 'text-emerald-400', ring: 'border-emerald-500/40', bg: 'bg-emerald-500/10', Icon: CheckCircle2, label: 'Healthy' },
  warning: { color: 'text-amber-400', ring: 'border-amber-500/40', bg: 'bg-amber-500/10', Icon: AlertTriangle, label: 'Warning' },
  critical: { color: 'text-red-400', ring: 'border-red-500/50', bg: 'bg-red-500/10', Icon: XCircle, label: 'Critical' },
};

const SERVICE_META = {
  backend: { label: 'Backend', Icon: Server },
  database: { label: 'Database', Icon: Database },
  image_batch: { label: 'Image Batch', Icon: ImageIcon },
  data_integrity: { label: 'Data Integrity', Icon: ShieldCheck },
  errors: { label: 'Server Errors', Icon: Activity },
};

const ServiceCard = ({ id, data }) => {
  const meta = SERVICE_META[id] || { label: id, Icon: Activity };
  const s = STATUS_STYLES[data.status] || STATUS_STYLES.ok;
  const extras = [];
  if (data.disk_pct != null) extras.push(`Disk ${data.disk_pct}%`);
  if (data.storage_mb != null) extras.push(`DB ${data.storage_mb} MB`);
  if (data.remaining != null) extras.push(`${data.remaining} images left`);
  if (id === 'image_batch') extras.push(data.running ? 'Running' : 'Paused');
  return (
    <div className={`rounded-xl border ${s.ring} ${s.bg} p-4`} data-testid={`health-card-${id}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-white font-semibold">
          <meta.Icon className="w-4 h-4 text-gray-300" />{meta.label}
        </div>
        <span className={`flex items-center gap-1 text-xs font-bold ${s.color}`} data-testid={`health-status-${id}`}>
          <s.Icon className="w-3.5 h-3.5" />{s.label}
        </span>
      </div>
      {data.detail ? <p className="text-sm text-gray-300">{data.detail}</p> : null}
      {extras.length > 0 && <p className="text-xs text-gray-500 mt-1">{extras.join(' · ')}</p>}
    </div>
  );
};

const HealthPanel = () => {
  const [health, setHealth] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const timer = useRef(null);

  const load = useCallback(async () => {
    try {
      const [h, inc] = await Promise.all([
        api.get('/admin/health'),
        api.get('/admin/health/incidents?limit=50'),
      ]);
      setHealth(h.data);
      setIncidents(inc.data || []);
    } catch (_e) {
      // transient under load; keep last snapshot
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(load, 30000);
    return () => clearInterval(timer.current);
  }, [load]);

  const checkNow = async () => {
    setChecking(true);
    try {
      const res = await api.post('/admin/health/check-now');
      setHealth(res.data);
      if (res.data.actions_taken?.length) {
        toast.success(`Watchdog fixed: ${res.data.actions_taken.join('; ')}`);
      } else {
        toast.success('Health check complete');
      }
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check failed (backend may be busy)');
    } finally {
      setChecking(false);
    }
  };

  const overall = health ? (STATUS_STYLES[health.overall] || STATUS_STYLES.ok) : STATUS_STYLES.ok;

  return (
    <div className="space-y-5" data-testid="health-panel">
      <div className={`rounded-xl border ${overall.ring} ${overall.bg} p-4 flex items-center justify-between flex-wrap gap-3`}>
        <div className="flex items-center gap-3">
          <overall.Icon className={`w-7 h-7 ${overall.color}`} />
          <div>
            <p className="text-lg font-bold text-white" data-testid="health-overall">
              System {overall.label}
            </p>
            <p className="text-xs text-gray-400">
              {health?.checked_at ? `Last checked ${new Date(health.checked_at).toLocaleTimeString()}` : 'Loading…'}
              {' · auto-refreshes every 30s'}
            </p>
          </div>
        </div>
        <Button onClick={checkNow} disabled={checking} className="bg-purple-600 hover:bg-purple-700" data-testid="health-check-now">
          <RefreshCw className={`w-4 h-4 mr-2 ${checking ? 'animate-spin' : ''}`} />
          Run check now
        </Button>
      </div>

      {loading && !health ? (
        <p className="text-gray-400 text-center py-8" data-testid="health-loading">Reading the app&apos;s vitals…</p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {health && Object.entries(health.services).map(([id, data]) => (
              <ServiceCard key={id} id={id} data={data} />
            ))}
          </div>

          {health?.actions_taken?.length > 0 && (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3" data-testid="health-actions">
              <p className="text-sm font-semibold text-emerald-300 mb-1">Auto-fixes this cycle</p>
              {health.actions_taken.map((a, i) => (
                <p key={i} className="text-xs text-gray-300">• {a}</p>
              ))}
            </div>
          )}

          <div>
            <h3 className="text-white font-semibold mb-2">Incident log</h3>
            {incidents.length === 0 ? (
              <p className="text-sm text-gray-500" data-testid="health-incidents-empty">
                No incidents recorded. All quiet.
              </p>
            ) : (
              <div className="space-y-2" data-testid="health-incidents">
                {incidents.map((inc) => {
                  const s = STATUS_STYLES[inc.severity] || STATUS_STYLES.ok;
                  return (
                    <div key={inc.id} className={`rounded-lg border ${s.ring} bg-black/20 px-3 py-2`} data-testid={`incident-${inc.id}`}>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] uppercase font-bold ${s.color}`}>{inc.severity}</span>
                        <span className="text-xs text-gray-500">{inc.category}</span>
                        <span className="text-xs text-gray-600 ml-auto">{new Date(inc.ts).toLocaleString()}</span>
                      </div>
                      <p className="text-sm text-gray-200">{inc.message}</p>
                      {inc.action_taken ? <p className="text-xs text-emerald-400 mt-0.5">Action: {inc.action_taken}</p> : null}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default HealthPanel;
