import React from 'react';
import { Clock, UserCheck, UserX } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * Applications tab — list of pending registration applications with
 * approve/reject buttons.
 *
 * Pure presentational: parent owns the list + handlers.
 */
const ApplicationsTab = ({ applications, actionLoading, onApprove, onReject, getStatusBadge }) => {
  if (applications.length === 0) {
    return (
      <div className="glass-dark p-12 rounded-xl text-center" data-testid="applications-empty">
        <Clock className="w-16 h-16 text-gray-500 mx-auto mb-4" />
        <p className="text-gray-400">No pending applications</p>
      </div>
    );
  }

  return (
    <>
      {applications.map((app) => (
        <div key={app.id} className="glass-dark p-6 rounded-xl" data-testid={`application-${app.id}`}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold text-white">{app.username}</h3>
              <p className="text-sm text-gray-400">{app.email}</p>
              <p className="text-xs text-gray-500 mt-1">
                Applied: {new Date(app.created_at).toLocaleDateString()}
              </p>
            </div>
            {getStatusBadge(app.status)}
          </div>

          <div className="mb-4">
            <p className="text-sm font-bold text-purple-300 mb-2">Application:</p>
            <p className="text-gray-300 bg-black/30 p-3 rounded">{app.application_text}</p>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={() => onApprove(app.id, app.username)}
              disabled={actionLoading[app.id]}
              className="bg-green-600 hover:bg-green-700"
              data-testid={`approve-${app.id}`}
            >
              <UserCheck className="w-4 h-4 mr-2" /> Approve
            </Button>
            <Button
              onClick={() => onReject(app.id, app.username)}
              disabled={actionLoading[app.id]}
              className="bg-red-600 hover:bg-red-700"
              data-testid={`reject-${app.id}`}
            >
              <UserX className="w-4 h-4 mr-2" /> Reject
            </Button>
          </div>
        </div>
      ))}
    </>
  );
};

export default ApplicationsTab;
