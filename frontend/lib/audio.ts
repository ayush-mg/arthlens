/**
 * ArthLens Tactile Micro-Acoustic Engine.
 *
 * Synthesizes procedural micro-sounds using the native Web Audio API.
 * - Zero external MP3/WAV network dependencies.
 * - Latency-free instant trigger.
 * - Fails silently in headless, mobile, or unsupported browser environments.
 * - Respects user preferences and global audio mute state.
 */

class TacticalAudioEngine {
  private ctx: AudioContext | null = null;
  private isMuted: boolean = true; // Default muted for accessibility & corporate policy

  constructor() {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('arthlens_audio_enabled');
      this.isMuted = stored !== 'true';
    }
  }

  private initContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    if (typeof window !== 'undefined') {
      localStorage.setItem('arthlens_audio_enabled', String(!this.isMuted));
      if (!this.isMuted) {
        this.playChime();
      }
    }
    return !this.isMuted;
  }

  public isEnabled(): boolean {
    return !this.isMuted;
  }

  /**
   * Crisp 30ms mechanical keyclick.
   */
  public playClick(freq: number = 800): void {
    if (this.isMuted) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const now = ctx.currentTime;

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now);
      osc.frequency.exponentialRampToValueAtTime(120, now + 0.03);

      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.03);
    } catch {
      // Fail-silent
    }
  }

  /**
   * Subtle 15ms high-frequency tick on interactive hover.
   */
  public playTick(): void {
    if (this.isMuted) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const now = ctx.currentTime;

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(1600, now);
      osc.frequency.exponentialRampToValueAtTime(800, now + 0.015);

      gain.gain.setValueAtTime(0.02, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.015);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.015);
    } catch {
      // Fail-silent
    }
  }

  /**
   * Two-tone harmonic chime for drawer open or data arrival.
   */
  public playChime(): void {
    if (this.isMuted) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      [587.33, 880].forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const start = now + idx * 0.06;

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.05, start);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.18);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(start);
        osc.stop(start + 0.18);
      });
    } catch {
      // Fail-silent
    }
  }

  /**
   * Resonant radar sonar ping for pilot geographic lock.
   */
  public playSonar(): void {
    if (this.isMuted) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const now = ctx.currentTime;

      osc.type = 'sine';
      osc.frequency.setValueAtTime(1244.51, now); // D#6
      osc.frequency.exponentialRampToValueAtTime(311.13, now + 0.4);

      gain.gain.setValueAtTime(0.07, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.4);
    } catch {
      // Fail-silent
    }
  }
}

export const audioEngine = new TacticalAudioEngine();

