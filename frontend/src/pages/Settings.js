import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { changePassword } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { KeyRound, ShieldCheck } from 'lucide-react';

const Settings = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [form, setForm] = useState({
    current_password: '',
    new_password: '',
    confirm_new_password: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.new_password.length < 6) {
      toast.error('New password must be at least 6 characters.');
      return;
    }
    if (form.new_password !== form.confirm_new_password) {
      toast.error('New passwords do not match.');
      return;
    }
    if (form.new_password === form.current_password) {
      toast.error('New password must be different from the current one.');
      return;
    }

    setLoading(true);
    try {
      await changePassword({
        current_password: form.current_password,
        new_password: form.new_password,
      });
      toast.success('Password updated. Please sign in again.');
      // Force re-auth — clear the httpOnly auth cookie + AuthContext state.
      await logout();
      setTimeout(() => navigate('/login'), 800);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-4 py-12 max-w-2xl">
        <header className="mb-8">
          <h1 className="text-4xl sm:text-5xl font-bold text-purple-300 flex items-center gap-3">
            <ShieldCheck className="w-10 h-10" />
            Account Settings
          </h1>
          <p className="text-gray-400 mt-2">
            Manage your account credentials. The Wardens of Delarom keep your keys safe.
          </p>
        </header>

        <section
          className="glass-dark p-6 sm:p-8 rounded-2xl border border-purple-500/30"
          data-testid="change-password-section"
        >
          <div className="flex items-center gap-3 mb-6">
            <KeyRound className="w-6 h-6 text-purple-300" />
            <h2 className="text-2xl font-bold text-white">Change Password</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="change-password-form">
            <div>
              <Label htmlFor="current_password" className="text-gray-300">
                Current Password
              </Label>
              <Input
                id="current_password"
                name="current_password"
                type="password"
                required
                autoComplete="current-password"
                value={form.current_password}
                onChange={handleChange}
                className="mt-1 bg-black/30 border-purple-500/40 text-white"
                data-testid="current-password-input"
              />
            </div>

            <div>
              <Label htmlFor="new_password" className="text-gray-300">
                New Password
              </Label>
              <Input
                id="new_password"
                name="new_password"
                type="password"
                required
                minLength={6}
                autoComplete="new-password"
                value={form.new_password}
                onChange={handleChange}
                className="mt-1 bg-black/30 border-purple-500/40 text-white"
                data-testid="new-password-input"
              />
              <p className="text-xs text-gray-500 mt-1">Minimum 6 characters.</p>
            </div>

            <div>
              <Label htmlFor="confirm_new_password" className="text-gray-300">
                Confirm New Password
              </Label>
              <Input
                id="confirm_new_password"
                name="confirm_new_password"
                type="password"
                required
                minLength={6}
                autoComplete="new-password"
                value={form.confirm_new_password}
                onChange={handleChange}
                className="mt-1 bg-black/30 border-purple-500/40 text-white"
                data-testid="confirm-new-password-input"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50"
              data-testid="change-password-submit"
            >
              {loading ? 'Updating…' : 'Update Password'}
            </Button>
          </form>

          <p className="text-xs text-gray-500 mt-4 italic">
            You will be signed out after changing your password and asked to sign in again.
          </p>
        </section>
      </div>
    </div>
  );
};

export default Settings;
