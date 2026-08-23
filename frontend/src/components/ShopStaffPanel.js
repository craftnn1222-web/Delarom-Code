import React, { useEffect, useState, useCallback } from 'react';
import { getShopEmployees, hireShopEmployee, fireShopEmployee } from '../utils/api';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Users, UserPlus, X, Coins } from 'lucide-react';

export const ROLE_META = {
  clerk: { label: 'Clerk', perk: 'Draws more NPC customers each cycle', icon: '🧍' },
  stocker: { label: 'Stocker', perk: 'Waives the auto-restock wholesale fee', icon: '📦' },
  barker: { label: 'Barker', perk: 'Customers buy more units per visit', icon: '📣' },
};
const WAGE = 50;

const ShopStaffPanel = ({ shopId }) => {
  const [employees, setEmployees] = useState([]);
  const [busy, setBusy] = useState('');
  const [playerRole, setPlayerRole] = useState('clerk');
  const [playerName, setPlayerName] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await getShopEmployees(shopId);
      setEmployees(res.data || []);
    } catch (_e) {
      // owner-only; ignore
    }
  }, [shopId]);

  useEffect(() => { load(); }, [load]);

  const hireNpc = async (role) => {
    setBusy(role);
    try {
      await hireShopEmployee(shopId, { role, kind: 'npc' });
      toast.success(`Hired an NPC ${ROLE_META[role].label}`);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not hire');
    } finally {
      setBusy('');
    }
  };

  const hirePlayer = async () => {
    const uname = playerName.trim();
    if (!uname) { toast.error("Enter the player's username"); return; }
    setBusy('player');
    try {
      await hireShopEmployee(shopId, { role: playerRole, kind: 'player', player_username: uname });
      toast.success(`Hired ${uname} as ${ROLE_META[playerRole].label}`);
      setPlayerName('');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not hire player');
    } finally {
      setBusy('');
    }
  };

  const fire = async (emp) => {
    setBusy(emp.id);
    try {
      await fireShopEmployee(shopId, emp.id);
      toast.info(`${emp.name} was let go`);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not fire');
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="glass-dark p-6 rounded-xl" data-testid="shop-staff-panel">
      <div className="flex items-center gap-2 mb-1">
        <Users className="w-5 h-5 text-amber-300" />
        <h3 className="text-xl font-bold text-amber-200">Employees ({employees.length})</h3>
      </div>
      <p className="text-sm text-gray-400 mb-4">
        Hire staff for a perk. Each is paid <span className="text-amber-300 font-semibold">{WAGE}g</span> per cycle — unpaid staff go idle that cycle. Player staff actually pocket their wage.
      </p>

      <div className="grid sm:grid-cols-3 gap-3 mb-5">
        {Object.entries(ROLE_META).map(([role, meta]) => (
          <div key={role} className="bg-black/20 border border-amber-500/20 rounded-lg p-3 flex flex-col">
            <div className="text-sm font-bold text-white mb-1">{meta.icon} {meta.label}</div>
            <div className="text-xs text-gray-400 flex-1 mb-3">{meta.perk}</div>
            <Button
              onClick={() => hireNpc(role)}
              disabled={busy === role}
              size="sm"
              className="bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800"
              data-testid={`hire-${role}-btn`}
            >
              <UserPlus className="w-3.5 h-3.5 mr-1" />
              Hire NPC ({WAGE}g)
            </Button>
          </div>
        ))}
      </div>

      {/* Hire a real player onto payroll */}
      <div className="bg-black/20 border border-purple-500/20 rounded-lg p-3 mb-5" data-testid="hire-player-form">
        <div className="text-sm font-bold text-white mb-2">Put a player on payroll</div>
        <div className="flex flex-col sm:flex-row gap-2">
          <Select value={playerRole} onValueChange={setPlayerRole}>
            <SelectTrigger className="bg-black/30 border-purple-500/30 sm:w-40" data-testid="player-role-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ROLE_META).map(([role, meta]) => (
                <SelectItem key={role} value={role} data-testid={`player-role-${role}`}>{meta.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Player username"
            className="bg-black/30 border-purple-500/30 flex-1"
            data-testid="player-username-input"
          />
          <Button
            onClick={hirePlayer}
            disabled={busy === 'player'}
            className="bg-gradient-to-r from-purple-700 to-pink-700 hover:from-purple-800 hover:to-pink-800"
            data-testid="hire-player-btn"
          >
            <UserPlus className="w-3.5 h-3.5 mr-1" />
            Hire player
          </Button>
        </div>
      </div>

      {employees.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-2" data-testid="staff-empty">
          No staff yet. Hire someone to boost your shop.
        </p>
      ) : (
        <div className="space-y-2">
          {employees.map((emp) => (
            <div
              key={emp.id}
              className="flex items-center gap-3 bg-black/20 border border-white/10 rounded-lg px-3 py-2"
              data-testid={`employee-row-${emp.id}`}
            >
              <span className="text-lg">{ROLE_META[emp.role]?.icon || '👤'}</span>
              <div className="flex-1 min-w-0">
                <p className="text-white font-semibold truncate flex items-center gap-2">
                  {emp.name}
                  <span
                    className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${
                      emp.player_user_id ? 'bg-purple-900/50 text-purple-200' : 'bg-gray-700/60 text-gray-300'
                    }`}
                    data-testid={`employee-kind-${emp.id}`}
                  >
                    {emp.player_user_id ? 'Player' : 'NPC'}
                  </span>
                </p>
                <p className="text-xs text-gray-400">
                  {ROLE_META[emp.role]?.label || emp.role} ·{' '}
                  <span className={emp.paid_this_cycle ? 'text-green-400' : 'text-yellow-500'}>
                    {emp.paid_this_cycle ? 'Working' : 'Awaiting first pay'}
                  </span>
                </p>
              </div>
              <span className="text-xs text-amber-300 flex items-center gap-1">
                <Coins className="w-3.5 h-3.5" />{emp.wage}/cycle
              </span>
              <Button
                onClick={() => fire(emp)}
                disabled={busy === emp.id}
                variant="ghost"
                size="sm"
                className="text-red-300 hover:bg-red-900/30"
                data-testid={`fire-${emp.id}-btn`}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ShopStaffPanel;
