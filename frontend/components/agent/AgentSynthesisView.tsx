import React from 'react';

export function AgentSynthesisView({ content }: { content: string }) {
	if (!content) return null;

	const lines = content.split('\n');
	const renderedElements: React.ReactNode[] = [];
	let currentList: { key: string; value: string; isMetric: boolean }[] = [];

	const flushList = (idx: number) => {
		if (currentList.length === 0) return;
		renderedElements.push(
			<div key={`list-${idx}`} className="my-2.5 space-y-1.5 pl-1">
				{currentList.map((item, itemIdx) => (
					<div
						key={itemIdx}
						className="flex items-start gap-2.5 p-2 rounded-none bg-white border border-[#231412]/20 shadow-[2px_2px_0px_#231412]/10"
					>
						<span className="w-1.5 h-1.5 mt-2 rounded-full bg-[#C8281E] shrink-0" />
						<div className="text-xs leading-relaxed text-[#231412] flex-1">
							{item.key && (
								<strong className="font-bold font-mono text-[#231412] mr-1.5 uppercase text-[11px] tracking-wide">
									{item.key}:
								</strong>
							)}
							<span>{renderInlineFormatting(item.value)}</span>
						</div>
					</div>
				))}
			</div>
		);
		currentList = [];
	};

	const renderInlineFormatting = (text: string): React.ReactNode => {
		const parts: React.ReactNode[] = [];
		const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
		let lastIdx = 0;
		let match;

		while ((match = regex.exec(text)) !== null) {
			if (match.index > lastIdx) {
				parts.push(text.substring(lastIdx, match.index));
			}
			const token = match[0];
			if (token.startsWith('**') && token.endsWith('**')) {
				parts.push(
					<strong key={match.index} className="font-extrabold text-[#231412]">
						{token.slice(2, -2)}
					</strong>
				);
			} else if (token.startsWith('*') && token.endsWith('*')) {
				parts.push(
					<em key={match.index} className="italic text-[#6E524D]">
						{token.slice(1, -1)}
					</em>
				);
			} else if (token.startsWith('`') && token.endsWith('`')) {
				parts.push(
					<code
						key={match.index}
						className="font-mono text-[11px] px-1 py-0.5 bg-[#FAF7F2] border border-[#231412]/30 text-[#C8281E] font-bold"
					>
						{token.slice(1, -1)}
					</code>
				);
			}
			lastIdx = regex.lastIndex;
		}
		if (lastIdx < text.length) {
			parts.push(text.substring(lastIdx));
		}
		return parts.length > 0 ? parts : text;
	};

	lines.forEach((rawLine, idx) => {
		const line = rawLine.trim();

		if (!line) {
			flushList(idx);
			return;
		}

		if (line.startsWith('### ') || line.startsWith('## ')) {
			flushList(idx);
			const title = line.replace(/^#{2,4}\s+/, '');
			renderedElements.push(
				<div
					key={`h3-${idx}`}
					className="mt-4 mb-2 flex items-center gap-2 border-b-2 border-[#231412] pb-1"
				>
					<span className="w-2.5 h-2.5 bg-[#C8281E]" />
					<h3 className="font-mono text-xs font-black uppercase tracking-wider text-[#231412]">
						{title}
					</h3>
				</div>
			);
			return;
		}

		if (line.startsWith('#### ')) {
			flushList(idx);
			const title = line.replace(/^####\s+/, '');
			renderedElements.push(
				<h4
					key={`h4-${idx}`}
					className="mt-3 mb-1 text-xs font-bold uppercase tracking-wide text-[#5C403B] flex items-center gap-1.5"
				>
					<span className="text-[#C8281E]">§</span>
					<span>{title}</span>
				</h4>
			);
			return;
		}

		if (
			line.includes('Recommendation:') ||
			line.startsWith('🔴') ||
			line.startsWith('🟢') ||
			line.startsWith('🟡')
		) {
			flushList(idx);
			const isHighRisk = line.includes('HIGH RISK') || line.includes('NOT_FEASIBLE') || line.includes('🔴');
			const isPass = (line.includes('FEASIBLE') && !line.includes('NOT')) || line.includes('VERIFIED') || line.includes('INFORMATIONAL') || line.includes('🟢');
			const bannerBg = isHighRisk ? 'bg-red-50 border-red-800 text-red-950' : isPass ? 'bg-emerald-50 border-emerald-800 text-emerald-950' : 'bg-amber-50 border-amber-800 text-amber-950';

			renderedElements.push(
				<div
					key={`banner-${idx}`}
					className={`my-3 p-3.5 border-2 ${bannerBg} shadow-[3px_3px_0px_#231412] flex items-start gap-2.5`}
				>
					<span className="text-base leading-none">
						{isHighRisk ? '🔴' : isPass ? '🟢' : '🟡'}
					</span>
					<div className="font-mono font-bold text-xs uppercase tracking-tight leading-relaxed">
						{renderInlineFormatting(line.replace(/^[🔴🟢🟡]\s*/, ''))}
					</div>
				</div>
			);
			return;
		}

		if (line.startsWith('- ') || line.startsWith('* ')) {
			const bulletText = line.substring(2).trim();
			const colonMatch = bulletText.match(/^\*\*([^*]+)\*\*:\s*(.*)$/);
			if (colonMatch) {
				currentList.push({
					key: colonMatch[1],
					value: colonMatch[2],
					isMetric: true,
				});
			} else {
				currentList.push({
					key: '',
					value: bulletText,
					isMetric: false,
				});
			}
			return;
		}

		flushList(idx);
		renderedElements.push(
			<p key={`p-${idx}`} className="text-xs leading-relaxed text-[#231412] my-1">
				{renderInlineFormatting(line)}
			</p>
		);
	});

	flushList(lines.length);

	return <div className="space-y-1">{renderedElements}</div>;
}
