'use client';

import React, { Suspense } from 'react';
import { AppWorkspace } from '../../components/AppWorkspace';
import { SmoothScrollProvider } from '../../components/motion/SmoothScrollProvider';

export default function DedicatedAppPage() {
  return (
    <SmoothScrollProvider>
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center bg-editorial-ivory text-editorial-charcoal font-mono text-sm">
            <div className="flex items-center space-x-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-editorial-forest border-t-transparent" />
              <span>Initializing ArthLens Epistemic Atlas...</span>
            </div>
          </div>
        }
      >
        <AppWorkspace standalone={true} />
      </Suspense>
    </SmoothScrollProvider>
  );
}
