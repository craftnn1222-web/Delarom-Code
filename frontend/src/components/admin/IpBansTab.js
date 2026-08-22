import React from 'react';
import { Globe, Plus } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * IP Bans tab (admin-only). List of banned IPs with reasons and unban action.
 */
const IpBansTab = ({ ipBans, onAddIpBan, onRemoveIpBan }) => (
  <>
    <div className="flex items-center justify-between mb-2">
      <h2 className="text-2xl font-bold text-red-300 flex items-center gap-2">
        <Globe className="w-5 h-5" />
        IP Bans ({ipBans.length})
      </h2>
      <Button
        size="sm"
        onClick={onAddIpBan}
        className="bg-gradient-to-r from-red-600 to-orange-600"
        data-testid="add-ip-ban-btn"
      >
        <Plus className="w-4 h-4 mr-1" /> Add IP Ban
      </Button>
    </div>

    {ipBans.length === 0 ? (
      <div className="glass-dark p-8 rounded-xl text-center text-gray-400" data-testid="ip-bans-empty">
        No IP addresses are currently banned.
      </div>
    ) : (
      <div className="space-y-3">
        {ipBans.map((ban) => (
          <div
            key={ban.id}
            className="glass-dark p-4 rounded-xl border border-red-500/30 flex items-center justify-between"
            data-testid={`ip-ban-${ban.id}`}
          >
            <div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-lg text-red-400">{ban.ip_address}</span>
                <span className="text-xs px-2 py-1 rounded-full bg-red-600/20 text-red-400 border border-red-600/40">
                  Banned
                </span>
              </div>
              <p className="text-sm text-gray-400 mt-1">Reason: {ban.reason}</p>
              <p className="text-xs text-gray-500 mt-1">
                Banned on: {new Date(ban.banned_at).toLocaleString()}
                {ban.associated_user_id && ` | Associated User ID: ${ban.associated_user_id}`}
              </p>
            </div>
            <Button
              onClick={() => onRemoveIpBan(ban.id)}
              size="sm"
              variant="outline"
              className="border-green-500/50 text-green-400 hover:bg-green-500/20"
            >
              Unban
            </Button>
          </div>
        ))}
      </div>
    )}
  </>
);

export default IpBansTab;
