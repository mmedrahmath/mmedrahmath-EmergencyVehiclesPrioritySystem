/**
 * EVPS - Web Audio API Synthesizer Sound FX
 * Zero external audio files required. Uses Web Audio API oscillator synthesis.
 * Team: PHANTOM DELUX
 */

class EVPSSoundFX {
  constructor() {
    this.ctx = null;
    this.isMuted = false;
    this.sirenLoopActive = false;
    this.sirenInterval = null;
  }

  _initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      this.stopSiren();
    }
    return this.isMuted;
  }

  // 1. Approaching Junction Radar Ping
  playRadarPing() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, this.ctx.currentTime); // A5
      osc.frequency.exponentialRampToValueAtTime(1760, this.ctx.currentTime + 0.12);

      gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.25);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start();
      osc.stop(this.ctx.currentTime + 0.25);
    } catch (e) {
      console.warn("Audio error:", e);
    }
  }

  // 2. Priority Granted Green Chime (Upbeat chord)
  playGreenGrantedChime() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    notes.forEach((freq, idx) => {
      setTimeout(() => {
        try {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();

          osc.type = 'triangle';
          osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

          gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.4);

          osc.connect(gain);
          gain.connect(this.ctx.destination);

          osc.start();
          osc.stop(this.ctx.currentTime + 0.4);
        } catch (e) {}
      }, idx * 70);
    });
  }

  // 3. Junction Cleared Chime
  playClearedChime() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    const notes = [783.99, 1046.50]; // G5 -> C6
    notes.forEach((freq, idx) => {
      setTimeout(() => {
        try {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();

          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

          gain.gain.setValueAtTime(0.18, this.ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.35);

          osc.connect(gain);
          gain.connect(this.ctx.destination);

          osc.start();
          osc.stop(this.ctx.currentTime + 0.35);
        } catch (e) {}
      }, idx * 100);
    });
  }

  // 4. Emergency Siren Loop (Toggleable)
  toggleSiren() {
    if (this.sirenLoopActive) {
      this.stopSiren();
      return false;
    } else {
      this.startSiren();
      return true;
    }
  }

  startSiren() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;
    this.sirenLoopActive = true;

    let high = false;
    const playTone = () => {
      if (!this.sirenLoopActive) return;
      try {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(high ? 960 : 770, this.ctx.currentTime);

        gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
        gain.gain.linearRampToValueAtTime(0.01, this.ctx.currentTime + 0.35);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start();
        osc.stop(this.ctx.currentTime + 0.35);
        high = !high;
      } catch (e) {}
    };

    playTone();
    this.sirenInterval = setInterval(playTone, 380);
  }

  stopSiren() {
    this.sirenLoopActive = false;
    if (this.sirenInterval) {
      clearInterval(this.sirenInterval);
      this.sirenInterval = null;
    }
  }
}

window.evpsAudio = new EVPSSoundFX();
