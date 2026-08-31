import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const Register = () => {
  const navigate = useNavigate();
  const { login: setAuthUser } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    application_text: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await register(formData);
      setAuthUser(response.data.access_token, response.data.user);
      toast.success('Welcome to Delarom! Your journey begins.');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center">
      <AnimatedBackground />
      
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="glass-dark p-8 rounded-2xl">
          <h1 className="text-4xl font-bold text-center mb-2 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600" data-testid="register-title">
            Begin Your Journey
          </h1>
          <p className="text-center text-gray-400 mb-6">Create your account in Delarom</p>

          <form onSubmit={handleSubmit} className="space-y-4" data-testid="register-form">
            <div>
              <Label htmlFor="username" className="text-gray-300">Username</Label>
              <Input
                id="username"
                name="username"
                type="text"
                value={formData.username}
                onChange={handleChange}
                required
                className="bg-black/20 border-purple-500/30 text-white"
                placeholder="Enter your username"
                data-testid="username-input"
              />
            </div>

            <div>
              <Label htmlFor="email" className="text-gray-300">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="bg-black/20 border-purple-500/30 text-white"
                placeholder="Enter your email"
                data-testid="email-input"
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-gray-300">Password</Label>
              <Input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="bg-black/20 border-purple-500/30 text-white"
                placeholder="Enter your password"
                data-testid="password-input"
              />
            </div>

            <div>
              <Label htmlFor="application_text" className="text-gray-300">Character Intro <span className="text-gray-500">(optional)</span></Label>
              <textarea
                id="application_text"
                name="application_text"
                value={formData.application_text}
                onChange={handleChange}
                rows="4"
                className="w-full bg-black/20 border border-purple-500/30 text-white rounded-md p-2 resize-none"
                placeholder="Tell us about your character or why you're joining (optional)..."
                data-testid="application-input"
              />
              <p className="text-xs text-gray-500 mt-1">Optional — you can start role-playing right away</p>
            </div>

            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              disabled={loading}
              data-testid="register-submit-btn"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6 text-center text-gray-400">
            Already have an account?{' '}
            <Link to="/login" className="text-purple-400 hover:text-purple-300" data-testid="login-link">
              Login here
            </Link>
          </div>

          <div className="mt-4 text-center">
            <Link to="/" className="text-gray-500 hover:text-gray-400 text-sm">
              ← Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;