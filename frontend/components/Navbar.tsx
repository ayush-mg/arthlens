'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Compass,
  MapPin,
  ShieldCheck,
  Layers,
  Network,
  LogOut,
  ChevronDown,
  Key,
  X,
  Lock,
  Eye,
  EyeOff,
  User,
  Volume2,
  VolumeX,
  FlaskConical,
  FileText,
  Cpu,
  FileCheck2,
  Users,
} from 'lucide-react';
import { UserManagementModal } from './UserManagementModal';
import { UserProfile, isDevAutoAuthEnabled, loginUser, registerUser } from '../lib/api';
import { audioEngine } from '../lib/audio';

interface NavbarProps {
  currentTab: 'atlas' | 'graph' | 'scenarios' | 'policy' | 'agent';
  onTabChange: (tab: 'atlas' | 'graph' | 'scenarios' | 'policy' | 'agent') => void;
  selectedGeoName: string;
  selectedGeoId: string;
  user?: UserProfile | null;
  onSwitchAccount?: (role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN', password?: string) => Promise<void>;
  onLogout?: () => Promise<void>;
  role?: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN';
  onRoleChange?: (role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN') => void;
  onLogin?: (user: UserProfile) => void;
  onOpenReport?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onTabChange,
  selectedGeoName,
  selectedGeoId,
  user,
  onSwitchAccount,
  onLogout,
  role = 'ENTREPRENEUR',
  onRoleChange,
  onLogin,
  onOpenReport,
}) => {
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [userManagementOpen, setUserManagementOpen] = useState(false);

  useEffect(() => {
    setAudioEnabled(audioEngine.isEnabled());
  }, []);

  const handleToggleAudio = () => {
    const nextState = audioEngine.toggleMute();
    setAudioEnabled(nextState);
  };

  const activeRole = user?.roles?.[0] || role;
  const devAuthEnabled = isDevAutoAuthEnabled();

  const handleRoleSelect = async (newRole: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN') => {
    setAccountMenuOpen(false);
    if (onSwitchAccount) {
      await onSwitchAccount(newRole);
    }
    if (onRoleChange) {
      onRoleChange(newRole);
    }
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setIsSubmitting(true);
    try {
      if (authMode === 'login') {
        const authenticated = await loginUser(loginEmail.trim(), loginPassword);
        setLoginModalOpen(false);
        setLoginPassword('');
        if (onLogin) {
          onLogin(authenticated);
        }
        if (onRoleChange && authenticated.roles.length > 0) {
          onRoleChange(authenticated.roles[0] as any);
        }
      } else {
        if (regPassword.length < 8) {
          setLoginError('Password must be at least 8 characters long.');
          setIsSubmitting(false);
          return;
        }
        const registered = await registerUser(regFullName.trim(), regEmail.trim(), regPassword);
        setLoginModalOpen(false);
        setRegPassword('');
        if (onLogin) {
          onLogin(registered);
        }
        if (onRoleChange && registered.roles.length > 0) {
          onRoleChange(registered.roles[0] as any);
        }
      }
    } catch (err: any) {
      setLoginError(err.message || 'Operation failed. Please verify inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-editorial-brass/30 bg-editorial-forest text-editorial-ivory shadow-editorial">
        <div className="flex h-16 items-center justify-between px-2 sm:px-4 lg:px-6 max-w-full overflow-hidden">
          {/* Left: Cartographic Editorial Masthead */}
          <div className="flex items-center space-x-2 sm:space-x-4 shrink-0">
            <Link
              href="/"
              title="Return to Overview"
              onClick={() => audioEngine.playClick(900)}
              className="flex items-center space-x-2 sm:space-x-3 group cursor-pointer"
            >
              <div className="flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded border border-editorial-brass/50 bg-editorial-forest-dark text-editorial-brass shadow-sm shrink-0 group-hover:border-editorial-brass transition-colors">
                <Compass className="h-4 w-4 sm:h-5 sm:w-5 animate-pulse-subtle" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="font-serif text-base sm:text-lg font-bold tracking-wide text-editorial-ivory group-hover:text-editorial-brass-light transition-colors">
                    ArthLens
                  </span>
                  <span className="hidden min-[480px]:inline-block border border-editorial-brass/40 bg-editorial-brass/15 px-1 sm:px-1.5 py-0.2 sm:py-0.5 font-mono text-[8px] sm:text-[9px] font-bold tracking-widest text-editorial-brass-light uppercase">
                    Epistemic Atlas
                  </span>
                </div>
                <p className="text-[10px] font-mono tracking-wider text-editorial-sage-light/80 hidden lg:block">
                  National Spatial & Financial Intelligence
                </p>
              </div>
            </Link>

            <div className="hidden h-7 w-px bg-editorial-brass/30 lg:block" />

            {/* Active Territory Scope Pill */}
            <div className="hidden items-center space-x-2 rounded border border-editorial-brass/30 bg-editorial-forest-dark/80 px-3 py-1 xl:flex text-xs">
              <MapPin className="h-3.5 w-3.5 text-editorial-copper-light" />
              <span className="font-medium text-editorial-ivory">{selectedGeoName}</span>
              <span className="font-mono text-[10px] text-editorial-brass">({selectedGeoId})</span>
            </div>
          </div>

          {/* Center: View Mode Switcher (Responsive 5-tab cockpit) */}
          <div className="flex items-center rounded border border-editorial-brass/30 bg-editorial-forest-dark p-0.5 shadow-inner">
            <button
              type="button"
              aria-label="Atlas Map Workspace"
              onClick={() => {
                audioEngine.playClick(900);
                onTabChange('atlas');
              }}
              className={`flex items-center space-x-1 sm:space-x-1.5 rounded px-2 sm:px-2.5 py-1 text-xs font-mono font-semibold transition-all cursor-pointer ${
                currentTab === 'atlas'
                  ? 'bg-editorial-ivory text-editorial-forest font-bold shadow-sm'
                  : 'text-editorial-ivory/70 hover:text-editorial-ivory'
              }`}
            >
              <Layers className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden lg:inline">Atlas Map</span>
            </button>
            <button
              type="button"
              aria-label="Evidence Graph Workspace"
              onClick={() => {
                audioEngine.playClick(1100);
                onTabChange('graph');
              }}
              className={`flex items-center space-x-1 sm:space-x-1.5 rounded px-2 sm:px-2.5 py-1 text-xs font-mono font-semibold transition-all cursor-pointer ${
                currentTab === 'graph'
                  ? 'bg-editorial-copper text-editorial-ivory font-bold shadow-sm'
                  : 'text-editorial-ivory/70 hover:text-editorial-ivory'
              }`}
            >
              <Network className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden lg:inline">Evidence Graph</span>
            </button>
            <button
              type="button"
              aria-label="Scenario Lab Workspace"
              onClick={() => {
                audioEngine.playClick(950);
                onTabChange('scenarios');
              }}
              className={`hidden sm:flex items-center space-x-1 sm:space-x-1.5 rounded px-2 sm:px-2.5 py-1 text-xs font-mono font-semibold transition-all cursor-pointer ${
                currentTab === 'scenarios'
                  ? 'bg-editorial-ivory text-editorial-forest font-bold shadow-sm'
                  : 'text-editorial-ivory/70 hover:text-editorial-ivory'
              }`}
            >
              <FlaskConical className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden lg:inline">Scenario Lab</span>
            </button>
            <button
              type="button"
              aria-label="Policy Rules Workspace"
              onClick={() => {
                audioEngine.playClick(980);
                onTabChange('policy');
              }}
              className={`hidden sm:flex items-center space-x-1 sm:space-x-1.5 rounded px-2 sm:px-2.5 py-1 text-xs font-mono font-semibold transition-all cursor-pointer ${
                currentTab === 'policy'
                  ? 'bg-editorial-ivory text-editorial-forest font-bold shadow-sm'
                  : 'text-editorial-ivory/70 hover:text-editorial-ivory'
              }`}
            >
              <FileText className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden lg:inline">Policy Rules</span>
            </button>
            <button
              type="button"
              aria-label="Agent Console Workspace"
              onClick={() => {
                audioEngine.playClick(1020);
                onTabChange('agent');
              }}
              className={`hidden sm:flex items-center space-x-1 sm:space-x-1.5 rounded px-2 sm:px-2.5 py-1 text-xs font-mono font-semibold transition-all cursor-pointer ${
                currentTab === 'agent'
                  ? 'bg-editorial-forest-light text-editorial-ivory font-bold shadow-sm'
                  : 'text-editorial-ivory/70 hover:text-editorial-ivory'
              }`}
            >
              <Cpu className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden lg:inline">Agent Console</span>
            </button>
          </div>

          {/* Right: Authenticated User & Acoustic Controls */}
          <div className="relative flex items-center space-x-1.5 sm:space-x-3 shrink-0">
            {onOpenReport && (
              <button
                type="button"
                onClick={onOpenReport}
                title="Open Territorial Decision Dossier"
                className="hidden sm:inline-flex items-center space-x-1.5 rounded border border-editorial-brass/40 bg-editorial-forest-dark px-2.5 py-1 text-xs font-mono font-semibold text-editorial-brass hover:border-editorial-brass hover:text-editorial-brass-light transition-colors cursor-pointer shrink-0"
              >
                <FileCheck2 className="h-3.5 w-3.5" />
                <span>Dossier</span>
              </button>
            )}
            {/* Tactical Audio Toggle */}
            <button
              type="button"
              onClick={handleToggleAudio}
              title={audioEnabled ? 'Tactile Audio Active (Mute)' : 'Tactile Audio Muted (Enable)'}
              className="flex items-center space-x-1 rounded border border-editorial-brass/30 bg-editorial-forest-dark/80 px-1.5 sm:px-2 py-1 text-[11px] font-mono text-editorial-ivory/80 hover:text-editorial-ivory hover:border-editorial-brass transition-colors cursor-pointer shrink-0"
            >
              {audioEnabled ? (
                <Volume2 className="h-3.5 w-3.5 text-editorial-brass" />
              ) : (
                <VolumeX className="h-3.5 w-3.5 text-editorial-sage-light/60" />
              )}
              <span className="hidden lg:inline text-[9px] uppercase tracking-wider text-editorial-brass-light font-bold">
                {audioEnabled ? 'Audio ON' : 'Audio OFF'}
              </span>
            </button>
            {user ? (
              <div className="relative shrink-0">
                <button
                  type="button"
                  onClick={() => setAccountMenuOpen(!accountMenuOpen)}
                  className="flex items-center space-x-1 sm:space-x-2 rounded border border-editorial-brass/40 bg-editorial-forest-dark/90 px-1.5 sm:px-3 py-1 sm:py-1.5 text-xs font-mono transition-colors hover:border-editorial-brass text-editorial-ivory cursor-pointer shrink-0"
                  aria-label="User RBAC Role and Account Session"
                >
                  <ShieldCheck className="h-3.5 w-3.5 text-editorial-brass-light shrink-0" />
                  <span className="hidden xl:inline font-bold truncate max-w-[110px] 2xl:max-w-[160px]">{user.email}</span>
                  <span className="rounded bg-editorial-brass/25 px-1 sm:px-1.5 py-0.5 text-[9px] sm:text-[10px] font-bold text-editorial-brass-light border border-editorial-brass/40 uppercase">
                    {activeRole}
                  </span>
                  <ChevronDown className="h-3 w-3 text-editorial-brass/80" />
                </button>

                {accountMenuOpen && (
                  <div className="absolute right-0 mt-2 w-64 rounded border border-editorial-brass/40 bg-editorial-forest-dark p-2 shadow-editorial-lg z-50 text-xs">
                    <div className="border-b border-editorial-brass/20 pb-2 mb-2 px-2">
                      <p className="text-[10px] uppercase font-mono tracking-wider text-editorial-brass">
                        Verified Session
                      </p>
                      <p className="font-mono text-editorial-ivory truncate">{user.email}</p>
                      <p className="font-mono text-[10px] text-editorial-sage-light">
                        Authority: <span className="font-bold text-editorial-copper-light">{activeRole}</span>
                      </p>
                    </div>

                    {/* Role switching is gated: dev quick-switch buttons only in development */}
                    {devAuthEnabled && (
                      <div className="space-y-1 mb-2">
                        <p className="px-2 text-[10px] uppercase font-mono tracking-wider text-editorial-sage-light/70">
                          Dev Switch Role (Authenticated)
                        </p>
                        <button
                          type="button"
                          onClick={() => handleRoleSelect('ENTREPRENEUR')}
                          className={`flex w-full items-center justify-between px-2 py-1.5 rounded text-left font-mono transition-colors cursor-pointer ${
                            activeRole === 'ENTREPRENEUR'
                              ? 'bg-editorial-brass/20 text-editorial-brass-light font-bold'
                              : 'text-editorial-ivory hover:bg-editorial-forest'
                          }`}
                        >
                          <span>Entrepreneur</span>
                          <span className="text-[10px] text-editorial-sage-light">entrepreneur@</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRoleSelect('STEWARD')}
                          className={`flex w-full items-center justify-between px-2 py-1.5 rounded text-left font-mono transition-colors cursor-pointer ${
                            activeRole === 'STEWARD'
                              ? 'bg-editorial-brass/20 text-editorial-brass-light font-bold'
                              : 'text-editorial-ivory hover:bg-editorial-forest'
                          }`}
                        >
                          <span>Data Steward</span>
                          <span className="text-[10px] text-editorial-sage-light">steward@</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRoleSelect('ADMIN')}
                          className={`flex w-full items-center justify-between px-2 py-1.5 rounded text-left font-mono transition-colors cursor-pointer ${
                            activeRole === 'ADMIN'
                              ? 'bg-editorial-brass/20 text-editorial-brass-light font-bold'
                              : 'text-editorial-ivory hover:bg-editorial-forest'
                          }`}
                        >
                          <span>Administrator</span>
                          <span className="text-[10px] text-editorial-sage-light">admin@</span>
                        </button>
                      </div>
                    )}

                    <div className="space-y-1 border-t border-editorial-brass/20 pt-2">
                      {activeRole === 'ADMIN' && (
                        <button
                          type="button"
                          onClick={() => {
                            setAccountMenuOpen(false);
                            setUserManagementOpen(true);
                          }}
                          className="flex w-full items-center space-x-2 px-2 py-1.5 rounded text-editorial-brass-light hover:bg-editorial-forest font-mono text-left cursor-pointer font-bold"
                        >
                          <Users className="h-3.5 w-3.5 text-editorial-brass" />
                          <span>Manage Users & Roles...</span>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => {
                          setAccountMenuOpen(false);
                          setLoginModalOpen(true);
                        }}
                        className="flex w-full items-center space-x-2 px-2 py-1.5 rounded text-editorial-ivory hover:bg-editorial-forest font-mono text-left cursor-pointer"
                      >
                        <Key className="h-3.5 w-3.5 text-editorial-brass" />
                        <span>Authenticate Credentials...</span>
                      </button>

                      <button
                        type="button"
                        onClick={async () => {
                          setAccountMenuOpen(false);
                          if (onLogout) await onLogout();
                        }}
                        className="flex w-full items-center space-x-2 px-2 py-1.5 rounded text-editorial-copper-light hover:bg-editorial-forest font-mono text-left cursor-pointer"
                      >
                        <LogOut className="h-3.5 w-3.5" />
                        <span>Sign Out (Session Revoke)</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
                <span className="font-mono text-xs text-editorial-copper-light font-semibold hidden lg:inline">
                  Unauthenticated
                </span>
                <button
                  type="button"
                  data-testid="navbar-sign-in-btn"
                  onClick={() => setLoginModalOpen(true)}
                  className="rounded border border-editorial-brass bg-editorial-brass/20 px-2 sm:px-2.5 py-1 text-xs font-mono font-bold text-editorial-ivory hover:bg-editorial-brass/30 transition-colors cursor-pointer shrink-0"
                >
                  Sign In
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Production-Safe Authentication Dialog */}
      {loginModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-editorial-charcoal/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded border border-editorial-brass/40 bg-editorial-paper p-6 shadow-editorial-lg">
            <div className="flex items-center justify-between border-b border-editorial-brass/30 pb-3 mb-4">
              <div className="flex items-center space-x-2 text-editorial-forest">
                <Lock className="h-4 w-4 text-editorial-copper" />
                <h3 className="font-serif font-bold text-sm">
                  {authMode === 'login' ? 'Session Authentication' : 'Create Entrepreneur Account'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setLoginModalOpen(false)}
                className="text-editorial-charcoal-light hover:text-editorial-charcoal cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Mode Switch Tabs */}
            <div className="flex rounded border border-editorial-brass/30 p-0.5 bg-editorial-ivory mb-4 font-mono text-xs">
              <button
                type="button"
                onClick={() => {
                  setAuthMode('login');
                  setLoginError(null);
                }}
                className={`flex-1 py-1 text-center rounded font-semibold transition-colors cursor-pointer ${
                  authMode === 'login'
                    ? 'bg-editorial-forest text-editorial-ivory'
                    : 'text-editorial-charcoal-light hover:text-editorial-charcoal'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthMode('register');
                  setLoginError(null);
                }}
                className={`flex-1 py-1 text-center rounded font-semibold transition-colors cursor-pointer ${
                  authMode === 'register'
                    ? 'bg-editorial-forest text-editorial-ivory'
                    : 'text-editorial-charcoal-light hover:text-editorial-charcoal'
                }`}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className="space-y-3">
              {authMode === 'register' && (
                <div>
                  <label className="block text-[11px] font-mono text-editorial-charcoal-light mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="Aarav Sharma"
                    className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory px-3 py-1.5 font-mono text-xs text-editorial-charcoal focus:border-editorial-copper focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-[11px] font-mono text-editorial-charcoal-light mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={authMode === 'login' ? loginEmail : regEmail}
                  onChange={(e) =>
                    authMode === 'login' ? setLoginEmail(e.target.value) : setRegEmail(e.target.value)
                  }
                  placeholder={authMode === 'login' ? 'user@arthlens.org' : 'name@business.in'}
                  className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory px-3 py-1.5 font-mono text-xs text-editorial-charcoal focus:border-editorial-copper focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-editorial-charcoal-light mb-1">
                  Password {authMode === 'register' && '(min 8 chars)'}
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={authMode === 'register' ? 8 : undefined}
                    value={authMode === 'login' ? loginPassword : regPassword}
                    onChange={(e) =>
                      authMode === 'login' ? setLoginPassword(e.target.value) : setRegPassword(e.target.value)
                    }
                    placeholder="••••••••••••"
                    className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory px-3 py-1.5 pr-8 font-mono text-xs text-editorial-charcoal focus:border-editorial-copper focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-editorial-charcoal-light hover:text-editorial-charcoal cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>

              {loginError && (
                <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-2 text-[11px] font-mono text-editorial-copper">
                  {loginError}
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded border border-editorial-forest bg-editorial-forest py-2 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting
                    ? 'Processing...'
                    : authMode === 'login'
                    ? 'Sign In with Credentials'
                    : 'Register as Entrepreneur'}
                </button>
              </div>
            </form>

            <div className="mt-4 pt-3 border-t border-editorial-brass/20 text-center">
              <Link
                href={authMode === 'login' ? '/register' : '/login'}
                onClick={() => setLoginModalOpen(false)}
                className="text-[11px] font-mono text-editorial-forest hover:underline"
              >
                {authMode === 'login' ? 'Open dedicated registration page →' : 'Open dedicated sign in page →'}
              </Link>
            </div>
          </div>
        </div>
      )}

      <UserManagementModal
        isOpen={userManagementOpen}
        onClose={() => setUserManagementOpen(false)}
        currentUserId={user?.id}
      />
    </>
  );
};
