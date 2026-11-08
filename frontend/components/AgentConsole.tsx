'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Cpu, Lock, Play, RefreshCw, Terminal } from 'lucide-react';
import { audioEngine } from '../lib/audio';
import {
  AgentRunEventRecord,
  AgentRunRecord,
  createAgentRun,
  fetchAgentRun,
  fetchAgentRunEvents,
  startAgentRun,
  streamAgentRunEvents,
} from '../lib/api';

interface AgentConsoleProps {
  geoName: string;
  geoId: string;
  isAuthenticated: boolean;
  onSignIn?: () => void;
}

export const AgentConsole: React.FC<AgentConsoleProps> = ({
  geoId,
  isAuthenticated,
  onSignIn,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [run, setRun] = useState<AgentRunRecord | null>(null);
  const [events, setEvents] = useState<AgentRunEventRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const streamControllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => streamControllerRef.current?.abort(), []);

  const handleCreateRun = async () => {
    if (!isAuthenticated) {
      onSignIn?.();
      return;
    }
    audioEngine.playClick(1150);
    setIsCreating(true);
    setError(null);
    streamControllerRef.current?.abort();
    streamControllerRef.current = null;
    setIsStreaming(false);
    setRun(null);
    setEvents([]);
    try {
      const createdRun = await createAgentRun({
        territory: geoId,
        goal: 'Assess small-business feasibility using available verified data',
      });
      setRun(createdRun);
      const eventPage = await fetchAgentRunEvents(createdRun.id);
      setEvents(eventPage.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create or load the agent run.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleStream = async () => {
    if (!run) return;
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
      return;
    }

    const controller = new AbortController();
    streamControllerRef.current = controller;
    setIsStreaming(true);
    setError(null);
    try {
      await streamAgentRunEvents(
        run.id,
        events.at(-1)?.seq ?? 0,
        (event) => {
          setEvents((current) => (
            current.some((existing) => existing.seq === event.seq)
              ? current
              : [...current, event].sort((left, right) => left.seq - right.seq)
          ));
          const nextState = event.payload.to_state;
          if (typeof nextState === 'string') {
            setRun((current) => current ? { ...current, state: nextState } : current);
          }
        },
        controller.signal,
      );
      const updatedRun = await fetchAgentRun(run.id);
      setRun(updatedRun);
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        setError(err instanceof Error ? err.message : 'The agent-run event stream failed.');
      }
    } finally {
      if (streamControllerRef.current === controller) {
        streamControllerRef.current = null;
        setIsStreaming(false);
      }
    }
  };

  const handleRefreshRun = async () => {
    if (!run) return;
    setIsRefreshing(true);
    setError(null);
    try {
      const [updatedRun, eventPage] = await Promise.all([
      fetchAgentRun(run.id),
        fetchAgentRunEvents(run.id),
      ]);
      setRun(updatedRun);
      setEvents(eventPage.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to refresh the agent run.');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleStartRun = async () => {
    if (!run) return;
    audioEngine.playClick(1200);
    setIsStarting(true);
    setError(null);
    try {
      await startAgentRun(run.id);
      await handleRefreshRun();
      if (!isStreaming) {
        handleToggleStream();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start the agent run.');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory shadow-editorial p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-editorial-brass/30 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <Cpu className="h-5 w-5 text-editorial-copper" />
            <h2 className="font-serif text-lg font-bold text-editorial-forest">
              Agent Run Console
            </h2>
            <span className="rounded bg-editorial-brass/15 border border-editorial-brass/30 px-2 py-0.5 text-[10px] font-mono font-bold text-editorial-charcoal">
              LIFECYCLE PERSISTENCE
            </span>
          </div>
          <p className="mt-1 text-xs text-editorial-charcoal-light font-mono">
            Run state and audit events are loaded from the backend. Agent worker execution is not yet connected.
          </p>
        </div>
        {run && (
          <div className="rounded border border-editorial-brass/40 bg-editorial-paper px-3 py-1.5 text-xs font-mono">
            State: <strong className="text-editorial-forest">{run.state}</strong>
          </div>
        )}
      </div>

      {!isAuthenticated && (
        <div className="rounded border border-editorial-brass/50 bg-editorial-paper p-4 text-xs font-mono text-editorial-charcoal flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Lock className="h-4 w-4 text-editorial-copper" />
            <span>Sign in as ENTREPRENEUR to create a persisted run record.</span>
          </div>
          <button
            type="button"
            onClick={onSignIn}
            className="rounded border border-editorial-forest bg-editorial-forest px-3 py-1 text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer"
          >
            Sign In
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3 text-xs font-mono text-editorial-copper">
          <AlertCircle className="mr-2 inline h-4 w-4 align-text-bottom" />
          {error}
        </p>
      )}

      <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-4 space-y-4 shadow-sm font-mono text-xs">
        <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-3">
          <div className="flex items-center space-x-2 text-editorial-forest font-bold">
            <Terminal className="h-4 w-4 text-editorial-copper" />
            <span>Persisted Run Event Feed</span>
          </div>
          <div className="flex items-center gap-2">
            {run && (
              <button
                type="button"
                disabled={isRefreshing || isStreaming}
                onClick={handleRefreshRun}
                className="inline-flex items-center space-x-1.5 rounded border border-editorial-brass/50 px-3 py-1.5 font-bold text-editorial-charcoal hover:bg-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className="h-3 w-3" />
                <span>{isRefreshing ? 'Refreshing…' : 'Refresh'}</span>
              </button>
            )}
            {run && (
              <button
                type="button"
                onClick={handleToggleStream}
                className="inline-flex items-center space-x-1.5 rounded border border-editorial-brass/50 px-3 py-1.5 font-bold text-editorial-charcoal hover:bg-editorial-ivory transition-colors cursor-pointer"
              >
                <span>{isStreaming ? 'Stop live updates' : 'Listen for live events'}</span>
              </button>
            )}
            {run && run.state === 'CREATED' && (
              <button
                type="button"
                disabled={isStarting}
                onClick={handleStartRun}
                className="inline-flex items-center space-x-1.5 rounded border border-editorial-copper bg-editorial-copper px-3 py-1.5 font-bold text-editorial-ivory hover:bg-editorial-copper/90 transition-colors cursor-pointer disabled:opacity-50"
              >
                <Play className="h-3 w-3" />
                <span>{isStarting ? 'Starting…' : 'Start Execution'}</span>
              </button>
            )}
            <button
              type="button"
              disabled={isCreating || !isAuthenticated}
              onClick={handleCreateRun}
              className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest bg-editorial-forest px-3 py-1.5 font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer disabled:opacity-50"
            >
              <Play className="h-3 w-3" />
              <span>{isCreating ? 'Creating…' : 'Create Run Record'}</span>
            </button>
          </div>
        </div>

        {run && (
          <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-1">
            <p>Run ID: <span className="break-all">{run.id}</span></p>
            <p>State: {run.state}</p>
            <p>Steps: {run.steps_used} · Model calls: {run.model_calls_used} · Recorded cost: ${run.cost_usd.toFixed(4)}</p>
          </div>
        )}

        {!run && !isCreating && !error && (
          <p className="text-editorial-charcoal-light">
            No run has been created in this session.
          </p>
        )}

        {run && events.length === 0 && (
          <p className="text-editorial-charcoal-light">
            No lifecycle events have been recorded. Creation persisted the run in CREATED state; no worker has advanced it.
          </p>
        )}

        <div className="space-y-2.5">
          {events.map((event) => (
            <div
              key={event.seq}
              className="rounded border border-editorial-brass/30 bg-editorial-ivory/60 p-3 space-y-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-editorial-forest">
                  Event {event.seq}: {event.type}
                </span>
                <time className="text-[10px] text-editorial-charcoal-light">
                  {new Date(event.at).toLocaleString()}
                </time>
              </div>
              <pre className="whitespace-pre-wrap break-words text-[11px] text-editorial-charcoal">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
