'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {FormEvent,useEffect,useState} from 'react';
import {useParams,useRouter} from 'next/navigation';
import {Archive,ArchiveRestore,Trash2,AlertTriangle,ShieldAlert,Building2} from 'lucide-react';
import {businessApi,BusinessWorkspace} from '../../../../lib/business-api';
import {useToast} from '@/components/ui';

export default function WorkspaceSettingsPage(){
	const {toast}=useToast();
	const router=useRouter();
	const businessId=useParams().id as string;
	const [workspace,setWorkspace]=useState<BusinessWorkspace|null>(null);
	const [name,setName]=useState('');
	const [industry,setIndustry]=useState('');
	const [address,setAddress]=useState('');
	const [saving,setSaving]=useState(false);
	const [archiving,setArchiving]=useState(false);
	const [deleting,setDeleting]=useState(false);

	useEffect(()=>{
		businessApi.getWorkspace(businessId)
			.then((record)=>{
				setWorkspace(record);
				setName(record.name);
				setIndustry(record.industry);
				setAddress(record.address??'');
			})
			.catch((error:Error)=>toast.error(error.message));
	},[businessId,toast]);

	const save=async(event:FormEvent)=>{
		event.preventDefault();
		setSaving(true);
		try{
			const updated=await businessApi.updateWorkspace(businessId,{
				name:name.trim(),
				industry:industry.trim(),
				address:address.trim(),
			});
			setWorkspace(updated);
			toast.success('Workspace profile updated successfully');
		}catch(error){
			toast.error(`Workspace update failed: ${(error as Error).message}`);
		}finally{
			setSaving(false);
		}
	};

	const toggleArchive=async()=>{
		const willArchive=!workspace?.is_archived;
		const confirmMsg=willArchive
			?`Archive enterprise "${workspace?.name}"? It will be hidden from active workspaces and placed in read-only audit mode.`
			:`Restore enterprise "${workspace?.name}" back to active status?`;
		if(!window.confirm(confirmMsg))return;
		setArchiving(true);
		try{
			await businessApi.archiveWorkspace(businessId,willArchive);
			toast.success(willArchive?'Workspace archived and hidden from active list':'Workspace restored to active portfolio');
			router.push('/workspaces');
		}catch(error){
			toast.error(`Archive operation failed: ${(error as Error).message}`);
		}finally{
			setArchiving(false);
		}
	};

	const removeWorkspace=async()=>{
		const promptMsg=`PERMANENTLY DELETE enterprise "${workspace?.name}"?\n\nWARNING: This will permanently purge all double-entry journals, inventory batches, sales invoices, and decision records. This action CANNOT be undone.\n\nType the workspace name "${workspace?.name}" to confirm:`;
		const userInput=window.prompt(promptMsg);
		if(userInput!==workspace?.name){
			if(userInput!==null){
				toast.error('Workspace name does not match. Deletion cancelled.');
			}
			return;
		}
		setDeleting(true);
		try{
			await businessApi.deleteWorkspace(businessId);
			toast.success(`Enterprise "${workspace?.name}" deleted permanently`);
			router.push('/workspaces');
		}catch(error){
			toast.error(`Workspace deletion failed: ${(error as Error).message}`);
		}finally{
			setDeleting(false);
		}
	};

	const isArchived=Boolean(workspace?.is_archived);

	return(
		<main className="mx-auto max-w-4xl space-y-8 p-6 md:p-10 select-none">
			<header className="border-b-2 border-[#231412] pb-5">
				<div className="flex items-center gap-2 mb-2">
					<span className="px-2.5 py-0.5 bg-[#C8281E]/10 border border-[#C8281E]/20 text-[#C8281E] font-mono text-[10px] font-bold tracking-widest uppercase">
						WORKSPACE GOVERNANCE // 17
					</span>
					{isArchived&&(
						<span className="px-2.5 py-0.5 bg-[#C8281E] text-white font-mono text-[10px] font-bold tracking-widest uppercase">
							ARCHIVED (READ-ONLY)
						</span>
					)}
				</div>
				<h1 className="text-3xl font-black text-[#231412]">
					Enterprise Settings & Lifecycle
				</h1>
				<p className="mt-1 text-xs font-mono text-[#5C403B]">
					Manage entity identity parameters, sovereign ledger metadata, and archive/purge lifecycles.
				</p>
			</header>

			<form onSubmit={save} className="space-y-5 bg-white border-2 border-[#231412] p-6 shadow-[3px_3px_0px_#231412]">
				<div className="flex items-center gap-2 pb-3 border-b border-[#231412]/15">
					<Building2 size={16} className="text-[#C8281E]" />
					<h2 className="text-sm font-mono font-bold uppercase tracking-wider text-[#231412]">
						Enterprise Profile
					</h2>
				</div>
				<div>
					<label className="block text-xs font-mono font-bold uppercase tracking-wider text-[#231412] mb-1">
						Enterprise Name
					</label>
					<input
						required
						value={name}
						onChange={(e)=>setName(e.target.value)}
						disabled={isArchived}
						className="w-full bg-[#FAF7F2] border-2 border-[#231412] p-3 text-sm font-mono text-[#231412] focus:outline-none focus:border-[#C8281E] disabled:opacity-60"
					/>
				</div>
				<div>
					<label className="block text-xs font-mono font-bold uppercase tracking-wider text-[#231412] mb-1">
						Industry Classification
					</label>
					<input
						required
						value={industry}
						onChange={(e)=>setIndustry(e.target.value)}
						disabled={isArchived}
						className="w-full bg-[#FAF7F2] border-2 border-[#231412] p-3 text-sm font-mono text-[#231412] focus:outline-none focus:border-[#C8281E] disabled:opacity-60"
					/>
				</div>
				<div>
					<label className="block text-xs font-mono font-bold uppercase tracking-wider text-[#231412] mb-1">
						Operating Address & Registered Office
					</label>
					<textarea
						value={address}
						onChange={(e)=>setAddress(e.target.value)}
						disabled={isArchived}
						rows={3}
						className="w-full bg-[#FAF7F2] border-2 border-[#231412] p-3 text-sm font-mono text-[#231412] focus:outline-none focus:border-[#C8281E] disabled:opacity-60"
					/>
				</div>
				<div className="flex items-center justify-between pt-2">
					<span className="text-[10px] font-mono text-[#5C403B]">
						Currency: {workspace?.currency||'INR'} · FY-Start: {workspace?.financial_year_start||'04-01'}
					</span>
					<MotionButton
						type="submit"
						disabled={saving||isArchived}
						className="bg-[#231412] hover:bg-[#C8281E] text-white font-mono text-xs font-bold uppercase tracking-wider px-5 py-2.5 border-2 border-[#231412] shadow-[2px_2px_0px_#C8281E] transition-colors disabled:opacity-50"
					>
						{saving?'Synchronizing Profile...':'Save Profile Modifications'}
					</MotionButton>
				</div>
			</form>

			<section className="space-y-4">
				<div className="flex items-center gap-2">
					<AlertTriangle size={16} className="text-[#C8281E]" />
					<h2 className="text-sm font-mono font-bold uppercase tracking-wider text-[#231412]">
						Lifecycle & Danger Zone
					</h2>
				</div>

				<div className="bg-white border-2 border-[#231412] p-6 shadow-[3px_3px_0px_#231412] space-y-4">
					<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#231412]/15">
						<div className="space-y-1">
							<div className="flex items-center gap-2">
								<h3 className="text-sm font-mono font-bold text-[#231412]">
									{isArchived?'Restore Workspace from Archive':'Archive Workspace'}
								</h3>
								<span className={`px-2 py-0.5 text-[9px] font-mono font-bold ${isArchived?'bg-amber-100 text-amber-800 border border-amber-300':'bg-[#FAF7F2] text-[#5C403B] border border-[#231412]/20'}`}>
									{isArchived?'STATUS: CURRENTLY ARCHIVED':'STATUS: ACTIVE'}
								</span>
							</div>
							<p className="text-xs text-[#5C403B] max-w-xl">
								{isArchived
									?'Restoring unhides this enterprise from the active chronicle and unlocks full write operations.'
									:'Archiving hides this enterprise from your active workspace list and locks all double-entry journals into read-only audit mode.'}
							</p>
						</div>
						<MotionButton
							type="button"
							onClick={toggleArchive}
							disabled={archiving}
							className="shrink-0 inline-flex items-center gap-2 px-4 py-2 bg-[#FAF7F2] hover:bg-[#231412] text-[#231412] hover:text-white border-2 border-[#231412] font-mono text-xs font-bold transition-colors shadow-[2px_2px_0px_#231412]"
						>
							{isArchived?(
								<>
									<ArchiveRestore size={14} /> Restore to Active
								</>
							):(
								<>
									<Archive size={14} /> Archive Enterprise
								</>
							)}
						</MotionButton>
					</div>

					<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
						<div className="space-y-1">
							<div className="flex items-center gap-2">
								<h3 className="text-sm font-mono font-bold text-[#C8281E]">
									Permanently Delete Workspace
								</h3>
								<span className="px-2 py-0.5 bg-red-100 text-red-800 border border-red-300 text-[9px] font-mono font-bold">
									IRREVERSIBLE
								</span>
							</div>
							<p className="text-xs text-[#5C403B] max-w-xl">
								Purge this workspace and every linked customer, supplier, transaction, FIFO inventory lot, and AI decision trace permanently.
							</p>
						</div>
						<MotionButton
							type="button"
							onClick={removeWorkspace}
							disabled={deleting}
							className="shrink-0 inline-flex items-center gap-2 px-4 py-2 bg-[#C8281E] hover:bg-[#A81E15] text-white border-2 border-[#231412] font-mono text-xs font-bold uppercase tracking-wider transition-colors shadow-[2px_2px_0px_#231412]"
						>
							<Trash2 size={14} />
							{deleting?'Purging Records...':'Delete Workspace'}
						</MotionButton>
					</div>
				</div>
			</section>
		</main>
	);
}