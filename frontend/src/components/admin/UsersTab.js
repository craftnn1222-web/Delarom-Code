import React from 'react';
import { Ban, AlertCircle, Eye, Trash2 } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * Users tab — user list with role/status badges and all admin actions.
 * Pure presentational: parent owns user data + handlers.
 */
const UsersTab = ({
  users,
  currentUser,
  actionLoading,
  onSuspend,
  onUnsuspend,
  onBan,
  onUnban,
  onPromote,
  onDemote,
  onResetPassword,
  onViewUser,
  onRemoveAccount,
  getRoleBadge,
  getStatusBadge,
}) => {
  const isAdmin = currentUser?.role === 'admin';

  return (
    <>
      {users.map((user) => {
        const status = user.status || 'active';
        const role = user.role || 'member';
        const busy = actionLoading[user.id];

        return (
          <div key={user.id} className="glass-dark p-6 rounded-xl" data-testid={`user-row-${user.id}`}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-white">{user.username}</h3>
                <p className="text-sm text-gray-400">{user.email}</p>
                <div className="flex gap-2 mt-2">
                  {getRoleBadge(role)}
                  {getStatusBadge(status)}
                </div>
              </div>
            </div>

            {status === 'banned' && user.ban_reason && (
              <div className="mb-4 p-3 bg-red-600/20 border border-red-600/30 rounded">
                <p className="text-sm text-red-400">
                  <Ban className="w-4 h-4 inline mr-2" />
                  <strong>Ban Reason:</strong> {user.ban_reason}
                </p>
              </div>
            )}

            {status === 'suspended' && user.suspension_reason && (
              <div className="mb-4 p-3 bg-yellow-600/20 border border-yellow-600/30 rounded">
                <p className="text-sm text-yellow-400">
                  <AlertCircle className="w-4 h-4 inline mr-2" />
                  <strong>Suspended:</strong> {user.suspension_reason}
                  {user.suspended_until && ` (Until ${new Date(user.suspended_until).toLocaleDateString()})`}
                </p>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {status === 'active' && role === 'member' && (
                <>
                  <Button onClick={() => onSuspend(user.id, user.username)} disabled={busy} size="sm" className="bg-yellow-600 hover:bg-yellow-700">
                    Suspend
                  </Button>
                  <Button onClick={() => onBan(user.id, user.username)} disabled={busy} size="sm" className="bg-red-600 hover:bg-red-700">
                    Ban
                  </Button>
                </>
              )}

              {status === 'suspended' && (
                <Button onClick={() => onUnsuspend(user.id, user.username)} disabled={busy} size="sm" className="bg-green-600 hover:bg-green-700">
                  Remove Suspension
                </Button>
              )}

              {status === 'banned' && (
                <Button onClick={() => onUnban(user.id, user.username)} disabled={busy} size="sm" className="bg-green-600 hover:bg-green-700">
                  Unban
                </Button>
              )}

              {isAdmin && role === 'member' && status === 'active' && (
                <Button onClick={() => onPromote(user.id, user.username)} disabled={busy} size="sm" className="bg-blue-600 hover:bg-blue-700">
                  Promote to Moderator
                </Button>
              )}

              {isAdmin && role === 'moderator' && (
                <Button onClick={() => onDemote(user.id, user.username)} disabled={busy} size="sm" className="bg-gray-600 hover:bg-gray-700">
                  Demote to Member
                </Button>
              )}

              {isAdmin && (
                <Button
                  onClick={() => onResetPassword(user.id, user.username, user.email)}
                  disabled={busy}
                  size="sm"
                  className="bg-purple-600 hover:bg-purple-700"
                  data-testid={`reset-password-${user.id}`}
                >
                  Reset Password
                </Button>
              )}

              {isAdmin && (
                <Button
                  onClick={() => onViewUser(user.id)}
                  disabled={busy}
                  size="sm"
                  variant="outline"
                  className="border-blue-500/50 text-blue-400 hover:bg-blue-500/20"
                  data-testid={`view-user-${user.id}`}
                >
                  <Eye className="w-3 h-3 mr-1" /> Details
                </Button>
              )}

              {isAdmin && user.role !== 'admin' && (
                <Button
                  onClick={() => onRemoveAccount(user.id, user.username, user.email)}
                  disabled={busy}
                  size="sm"
                  className="bg-red-700 hover:bg-red-800"
                  data-testid={`remove-account-${user.id}`}
                >
                  <Trash2 className="w-3 h-3 mr-1" /> Remove
                </Button>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
};

export default UsersTab;
