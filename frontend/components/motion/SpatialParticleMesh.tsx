'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

interface SpatialParticleMeshProps {
  className?: string;
  wireframeColor?: number;
  particleColor?: number;
  pointCount?: number;
}

/**
 * SpatialParticleMesh: Procedural Cartographic Geodetic Elevation Surface.
 * Renders an undulating digital terrain model with interactive cursor-driven topological deformation.
 * Note: Visualizes a mathematical topographic elevation metaphor; strictly never decorative points
 * masquerading as demographic observations.
 */
export const SpatialParticleMesh: React.FC<SpatialParticleMeshProps> = ({
  className = '',
  wireframeColor = 0xb89758, // Editorial brass
  particleColor = 0x203d32,  // Editorial deep forest
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [webGLSupported, setWebGLSupported] = useState(true);

  useEffect(() => {
    const container = mountRef.current;
    if (!container || typeof window === 'undefined') return;

    // Check reduced motion
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Check WebGL availability
    const hasWebGL = () => {
      try {
        const canvas = document.createElement('canvas');
        return !!(
          window.WebGLRenderingContext &&
          (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
        );
      } catch {
        return false;
      }
    };

    if (!hasWebGL()) {
      setWebGLSupported(false);
      return;
    }

    // Initialize Scene, Camera, Renderer
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
      });
    } catch {
      setWebGLSupported(false);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 9, 20);
    camera.lookAt(0, 0, 0);

    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 1. High-Density Procedural Geodetic Elevation Mesh
    const gridCols = 44;
    const gridRows = 32;
    const planeWidth = 26;
    const planeDepth = 20;
    const planeGeo = new THREE.PlaneGeometry(planeWidth, planeDepth, gridCols, gridRows);
    planeGeo.rotateX(-Math.PI / 2);

    const posAttr = planeGeo.attributes.position;
    const vertexCount = posAttr.count;
    const baseElevations = new Float32Array(vertexCount);
    const originalPositions = new Float32Array(vertexCount * 3);

    for (let i = 0; i < vertexCount; i++) {
      const x = posAttr.getX(i);
      const z = posAttr.getZ(i);
      originalPositions[i * 3] = x;
      originalPositions[i * 3 + 2] = z;

      // Mathematical geodetic terrain undulation (Doab river basin topological contour model)
      const baseElevation =
        Math.sin(x * 0.35) * Math.cos(z * 0.35) * 1.4 +
        Math.sin(x * 0.18 + z * 0.22) * 0.8 +
        Math.cos(Math.sqrt(x * x + z * z) * 0.4) * 0.4;

      baseElevations[i] = baseElevation;
      posAttr.setY(i, baseElevation);
      originalPositions[i * 3 + 1] = baseElevation;
    }
    planeGeo.computeVertexNormals();

    const planeMat = new THREE.MeshBasicMaterial({
      color: wireframeColor,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
    });
    const terrainMesh = new THREE.Mesh(planeGeo, planeMat);
    scene.add(terrainMesh);

    // 2. Geodetic Control Station Markers (Elevation Benchmarks)
    // Vertices at regular grid intervals act as cartographic geodetic datums
    const datumCount = Math.floor(vertexCount / 3);
    const datumGeo = new THREE.BufferGeometry();
    const datumPositions = new Float32Array(datumCount * 3);
    const datumIndices: number[] = [];

    let dIdx = 0;
    for (let i = 0; i < vertexCount; i += 3) {
      if (dIdx >= datumCount) break;
      datumPositions[dIdx * 3] = posAttr.getX(i);
      datumPositions[dIdx * 3 + 1] = posAttr.getY(i) + 0.08;
      datumPositions[dIdx * 3 + 2] = posAttr.getZ(i);
      datumIndices.push(i);
      dIdx++;
    }
    datumGeo.setAttribute('position', new THREE.BufferAttribute(datumPositions, 3));

    const datumMat = new THREE.PointsMaterial({
      color: particleColor,
      size: 0.14,
      transparent: true,
      opacity: 0.75,
    });
    const datumPoints = new THREE.Points(datumGeo, datumMat);
    scene.add(datumPoints);

    // Interactive Cursor Deformation State
    const mouseRay = new THREE.Vector2(0, 0);
    const planeIntersection = new THREE.Vector3(0, 0, 0);
    let targetRotY = 0;
    let targetRotX = 0;
    let hasMouseMoved = false;

    const handleMouseMove = (e: MouseEvent) => {
      hasMouseMoved = true;
      const rect = container.getBoundingClientRect();
      const normX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const normY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      mouseRay.x = normX;
      mouseRay.y = normY;

      // Project cursor ray to XZ terrain plane approximation
      planeIntersection.x = normX * (planeWidth * 0.45);
      planeIntersection.z = -normY * (planeDepth * 0.4);

      targetRotY = normX * 0.14;
      targetRotX = normY * 0.08;
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Resize Observer
    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // Animation Loop with Interactive Cursor Deformation
    let reqId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const elapsed = clock.getElapsedTime();

      if (!reducedMotion) {
        // Smooth camera dampening
        terrainMesh.rotation.y += (targetRotY - terrainMesh.rotation.y) * 0.04;
        terrainMesh.rotation.x += (targetRotX - terrainMesh.rotation.x) * 0.04;
        datumPoints.rotation.y = terrainMesh.rotation.y;
        datumPoints.rotation.x = terrainMesh.rotation.x;

        // Dynamic vertex deformation around interactive cursor coordinate
        const positions = planeGeo.attributes.position;
        const datums = datumGeo.attributes.position.array as Float32Array;

        const cursorX = planeIntersection.x;
        const cursorZ = planeIntersection.z;
        const interactionRadiusSq = 36.0; // 6-unit deformation radius

        for (let i = 0; i < vertexCount; i++) {
          const vx = originalPositions[i * 3];
          const vz = originalPositions[i * 3 + 2];
          const baseHeight = baseElevations[i];

          // Ambient subtle wave breathing
          const ambientWave = Math.sin(elapsed * 0.8 + vx * 0.4 + vz * 0.3) * 0.15;

          // Localized cursor displacement if user has moved mouse
          let cursorDisplacement = 0;
          if (hasMouseMoved) {
            const dx = vx - cursorX;
            const dz = vz - cursorZ;
            const distSq = dx * dx + dz * dz;
            if (distSq < interactionRadiusSq) {
              const falloff = 1 - distSq / interactionRadiusSq;
              cursorDisplacement = Math.sin(elapsed * 3.0 - Math.sqrt(distSq) * 1.5) * 0.6 * (falloff * falloff);
            }
          }

          positions.setY(i, baseHeight + ambientWave + cursorDisplacement);
        }
        positions.needsUpdate = true;

        // Update corresponding datum benchmark positions
        for (let j = 0; j < datumIndices.length; j++) {
          const vIdx = datumIndices[j];
          datums[j * 3 + 1] = positions.getY(vIdx) + 0.08;
        }
        datumGeo.attributes.position.needsUpdate = true;
      }

      renderer.render(scene, camera);
      reqId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      planeGeo.dispose();
      planeMat.dispose();
      datumGeo.dispose();
      datumMat.dispose();
      renderer.dispose();
    };
  }, [wireframeColor, particleColor]);

  if (!webGLSupported) {
    return (
      <div className={`absolute inset-0 bg-editorial-ivory opacity-20 pointer-events-none ${className}`}>
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="fallback-grid" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#b89758" strokeWidth="0.5" strokeOpacity="0.25" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#fallback-grid)" />
        </svg>
      </div>
    );
  }

  return (
    <div
      ref={mountRef}
      aria-hidden="true"
      className={`absolute inset-0 pointer-events-none overflow-hidden ${className}`}
    />
  );
};
