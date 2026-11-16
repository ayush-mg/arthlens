'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Building2, Plus, RefreshCw } from 'lucide-react';
import { BusinessWorkspace } from '../../lib/business-api';

export interface BusinessConstellationProps {
	workspaces: BusinessWorkspace[];
	error?: string | null;
	onRetry?: () => void;
	onCreateWorkspace?: () => void;
	onSelectWorkspace?: (workspace: BusinessWorkspace) => void;
}

export default function BusinessConstellation({
	workspaces,
	error = null,
	onRetry,
	onCreateWorkspace,
	onSelectWorkspace,
}: BusinessConstellationProps) {
	const router = useRouter();

	if (error) {
		return (
			<section data-testid="workspace-directory-error" className="rounded-2xl border border-rose-300/30 bg-rose-50 p-7 text-center shadow-sm">
				<h2 className="text-lg font-semibold text-rose-900">Workspaces could not be loaded</h2>
				<p className="mt-2 text-sm text-[#6E524D]">{error}</p>
				{onRetry && <MotionButton onClick={onRetry} className="mt-5 inline-flex items-center gap-2 rounded-xl border border-[#C8281E]/20 bg-white px-4 py-2 text-sm text-[#231412] shadow-sm hover:border-[#C8281E]"><RefreshCw size={15} /> Retry connection</MotionButton>}
			</section>
		);
	}

	if (workspaces.length === 0) {
		return (
			<section data-testid="workspace-directory-empty" className="rounded-2xl border border-dashed border-[#C8281E]/25 bg-white/80 px-6 py-12 text-center shadow-sm">
				<span className="mx-auto grid h-12 w-12 place-items-center rounded-xl border border-[#C8281E]/30 bg-[#C8281E]/[0.08] text-[#C8281E]"><Building2 size={21} /></span>
				<h2 className="mt-4 text-lg font-semibold text-[#231412]">No workspaces connected</h2>
				<p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[#6E524D]">Create a workspace to start recording business activity and viewing its financial position.</p>
				{onCreateWorkspace && <MotionButton onClick={onCreateWorkspace} className="liquid-primary-button mx-auto mt-5"><Plus size={15} /> Create workspace</MotionButton>}
			</section>
		);
	}

	return (
		<section aria-label="Business workspaces" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{workspaces.map((workspace) => (
				<MotionButton
					key={workspace.id}
					onClick={() => onSelectWorkspace ? onSelectWorkspace(workspace) : router.push('/workspaces/' + workspace.id)}
					className="group rounded-2xl border border-[#C8281E]/20 bg-white/90 p-5 text-left transition hover:-translate-y-1 hover:border-[#C8281E] hover:bg-white shadow-[0_12px_32px_rgba(200,40,30,0.06)]"
					aria-label={workspace.name}
				>
					<span className="flex items-center justify-between">
						<span className="grid h-10 w-10 place-items-center rounded-xl border border-[#C8281E]/30 bg-[#C8281E]/10 text-sm font-bold text-[#C8281E]">{workspace.name.slice(0, 1).toUpperCase()}</span>
						<ArrowRight size={15} className="text-[#9A7E78] transition group-hover:translate-x-1 group-hover:text-[#C8281E]" />
					</span>
					<strong className="mt-4 block text-base font-semibold text-[#231412]">{workspace.name}</strong>
					<span className="mt-1 block text-xs text-[#6E524D]">{workspace.industry || 'Business workspace'}</span>
					<span className="mt-3 block text-[11px] text-[#9A7E78]">{[workspace.district, workspace.state].filter(Boolean).join(', ') || 'Location not set'}</span>
				</MotionButton>
			))}
		</section>
	);
}