import { afterEach, describe, expect, it, vi } from 'vitest';

import { streamAgentRunEvents } from '../lib/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('agent-run SSE client', () => {
  it('parses persisted event frames split across network chunks', async () => {
    const encoder = new TextEncoder();
    const chunks = [
      'id: 4\nevent: TOOL_RETURNED\ndata: {"seq":4,"type":"TOOL_RETURNED",',
      '"payload":{"to_state":"OBSERVING"},"at":"2026-11-07T10:00:00Z"}\n\n',
      ': keep-alive\n\n',
    ];
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
        controller.close();
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const events: unknown[] = [];
    const controller = new AbortController();

    await streamAgentRunEvents('run-1', 3, (event) => events.push(event), controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/agent-runs/run-1/events/stream?after_sequence=3'),
      expect.objectContaining({
        credentials: 'include',
        signal: controller.signal,
      }),
    );
    expect(events).toEqual([{
      seq: 4,
      type: 'TOOL_RETURNED',
      payload: { to_state: 'OBSERVING' },
      at: '2026-11-07T10:00:00Z',
    }]);
  });

  it('rejects event records whose SSE id does not match their sequence', async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(
          'id: 5\nevent: TOOL_RETURNED\ndata: {"seq":4,"type":"TOOL_RETURNED","payload":{},"at":"2026-11-07T10:00:00Z"}\n\n',
        ));
        controller.close();
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    ));

    await expect(
      streamAgentRunEvents('run-1', 3, vi.fn(), new AbortController().signal),
    ).rejects.toThrow('ID/type did not match');
  });
});
