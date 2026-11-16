# KASH Celestial Asset Registry & Astronomical Attribution

This document catalogues all astronomical surface textures, elevation models, atmospheric layers, and deep-space star fields utilized by the **KASH Photorealistic Celestial Asset Engine**.

---

## 1. Solar Asset: The Central Star (Proprietor Core)

- **Asset Name:** `sun_photosphere_2k.jpg`
- **Celestial Body:** Sol (The Sun)
- **Primary Source:** NASA Solar Dynamics Observatory (SDO) / SOHO Consortium
- **Curated By:** Solar System Scope / NASA Goddard Space Flight Center
- **Original Resolution:** 2048 × 1024 (Optimized Equirectangular UV Map)
- **Local Path:** `/assets/cosmos/sun/sun_photosphere_2k.jpg`
- **Astronomical Features:** High-resolution solar granulation, active sunspot magnetic loops, limb darkening, and solar flare activity.
- **Attribution & License:** NASA Public Domain / SDO Science Team. Free for educational and commercial scientific visualization.

---

## 2. Planetary Assets: Businesses (The Planets)

### A. Earth (Planet 1: Primary Commercial Anchor)
- **Asset Names:**
  - Diffuse Albedo: `earth_albedo_2k.jpg` (NASA Visible Earth / Blue Marble Next Generation)
  - Cloud Layer: `earth_clouds_1k.png` (NASA GSFC Satellite Cloud Composite with Alpha Transparency)
  - Normal Map: `earth_normal_2k.jpg` (USGS / NASA GTOPO30 Topographic Vector Normal Map)
  - Specular Map: `earth_specular_2k.jpg` (NASA Ocean Water Specular Reflectivity Mask)
- **Primary Source:** NASA Earth Observatory (Visible Earth) & Three.js Examples Repository
- **Original Resolution:** 2048 × 1024 (Albedo, Normal, Specular); 1024 × 512 (Clouds)
- **Local Paths:**
  - `/assets/cosmos/planets/earth_albedo_2k.jpg`
  - `/assets/cosmos/planets/earth_clouds_1k.png`
  - `/assets/cosmos/planets/earth_normal_2k.jpg`
  - `/assets/cosmos/planets/earth_specular_2k.jpg`
- **Astronomical Features:** Dual-layer rendering with independently rotating atmospheric clouds, continental relief, ocean specular glare, and Rayleigh atmospheric scattering.
- **Attribution & License:** NASA Earth Observatory / Reto Stöckli / Robert Simmon. Public Domain.

### B. Mars (Planet 2: Frontier Venture Store)
- **Asset Name:** `mars_surface_2k.jpg`
- **Celestial Body:** Mars
- **Primary Source:** NASA / USGS Astrogeology Science Center / Mars Global Surveyor (MGS) MOC
- **Original Resolution:** 8192 × 4096 (Optimized to 2048 × 1024 for high-performance WebGL)
- **Local Path:** `/assets/cosmos/planets/mars_surface_2k.jpg`
- **Astronomical Features:** True-color ferric oxide crust, Valles Marineris canyon system, Olympus Mons volcanic plateau, and polar ice cap remnants.
- **Attribution & License:** NASA / JPL-Caltech / USGS. Public Domain.

### C. Jupiter (Planet 3: High-Volume Commercial Hub)
- **Asset Name:** `jupiter_surface_2k.jpg`
- **Celestial Body:** Jupiter
- **Primary Source:** NASA / JPL / Cassini Imaging Science Subsystem (ISS) & JunoCam (SwRI)
- **Original Resolution:** 8192 × 4096 (Optimized to 2048 × 1024)
- **Local Path:** `/assets/cosmos/planets/jupiter_surface_2k.jpg`
- **Astronomical Features:** Counter-rotating zonal storm bands, ammonia-cloud belts, cyclonic white ovals, and the Great Red Spot.
- **Attribution & License:** NASA / JPL-Caltech / Space Science Institute. Public Domain.

### D. Saturn (Planet 4: Ringed Wholesale Enterprise)
- **Asset Names:**
  - Surface: `saturn_surface_2k.jpg`
  - Ring System: `saturn_ring_alpha.png`
- **Celestial Body:** Saturn & Rings
- **Primary Source:** NASA / JPL / Cassini-Huygens Mission
- **Original Resolution:** 8192 × 4096 (Surface); 8192 × 64 (Radial Ring System Alpha Map)
- **Local Paths:**
  - `/assets/cosmos/planets/saturn_surface_2k.jpg`
  - `/assets/cosmos/rings/saturn_ring_alpha.png`
- **Astronomical Features:** Muted butterscotch atmospheric banding, Cassini Division ring gap, A/B/C main rings rendered as physical 3D geometric ring discs with transparent alpha channels.
- **Attribution & License:** NASA / JPL / Space Science Institute. Public Domain.

---

## 3. Lunar Asset: Customers (The Moons)

- **Asset Name:** `moon_lro_1k.jpg`
- **Celestial Body:** The Moon (Luna)
- **Primary Source:** NASA Lunar Reconnaissance Orbiter (LRO) / Lunar Orbiter Laser Altimeter (LOLA)
- **Curated By:** NASA Scientific Visualization Studio (SVS) & Three.js Planetary Textures
- **Original Resolution:** 1024 × 512 (Equirectangular UV Map)
- **Local Path:** `/assets/cosmos/moon/moon_lro_1k.jpg`
- **Astronomical Features:** Detailed basaltic lunar maria (Sea of Tranquility, Ocean of Storms), high-albedo crater impact ejecta rays (Tycho, Copernicus), and terminator shadow depth.
- **Attribution & License:** NASA SVS / Ernie Wright / LRO Science Team. Public Domain.

---

## 4. Deep Space Asset: Astronomical Background

- **Asset Name:** `milky_way_2k.jpg`
- **Field:** Milky Way Panoramic Galactic Plane & Deep Cosmic Skybox
- **Primary Source:** European Southern Observatory (ESO) / NASA Hubble Space Telescope
- **Original Resolution:** 2048 × 1024
- **Local Path:** `/assets/cosmos/stars/milky_way_2k.jpg`
- **Astronomical Features:** Dense galactic bulge stars, interstellar dust rifts, and diffuse cosmic nebulae.
- **Attribution & License:** ESO / S. Brunier / NASA. Creative Commons Attribution 4.0 / NASA Public Domain.

---

## 5. Cinematic Space Footage: NASA SVS Deep Space Video Background

- **Asset Identifiers & Local Paths:**
  - Full HD MP4: `/assets/cosmos/videos/cosmic_voyage_1080p.mp4` (1920 × 1080, H.264/AAC, ~8.5 MB)
  - HD MP4: `/assets/cosmos/videos/cosmic_voyage_720p.mp4` (1280 × 720, H.264/AAC, ~4.5 MB)
  - HD WebM: `/assets/cosmos/videos/cosmic_voyage_720p.webm` (1280 × 720, VP8/Vorbis, ~4.1 MB)
  - Static Poster Fallback: `/assets/cosmos/videos/cosmic_poster.jpg` (1024 × 576, ~72 KB)
- **Celestial Subject:** The Great Orion Nebula (Messier 42 / NGC 1976)
- **Primary Source:** NASA Scientific Visualization Studio (SVS Project ID: 30959)
- **Direct Official URL:** https://svs.gsfc.nasa.gov/30959/
- **Production Team & Collaborators:**
  - Frank Summers (STScI) - Lead Visualizer & Science
  - Greg Bacon (STScI) - 3D Animation & Modeling
  - Zolt Levay (STScI) - Imaging & Composite Astrophotography
  - Joseph DePasquale (STScI) - Multi-wavelength Processing
  - Lisa Frattare (STScI) - Outreach
  - Massimo Robberto (STScI) - Science Lead
  - Robert Hurt (IPAC/Caltech) - Infrared Data Synthesis
- **Telescopes & Instruments:**
  - NASA Hubble Space Telescope (Advanced Camera for Surveys)
  - NASA Spitzer Space Telescope (Infrared Array Camera & MIPS)
- **Astronomical Features:** Multi-wavelength 3D visualization depicting glowing interstellar hydrogen gas (ionized H II region), protostellar discs (proplyds), Herbig-Haro bow shocks, and dense cosmic dust filaments in the central cavity of the Orion molecular cloud.
- **Attribution & License:** NASA, ESA, STScI, F. Summers, G. Bacon, Z. Levay, J. DePasquale, L. Frattare, M. Robberto, and R. Hurt. NASA Public Domain / Free for non-commercial and educational scientific dissemination.

