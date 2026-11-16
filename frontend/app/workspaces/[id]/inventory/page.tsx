'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {useToast} from '@/components/ui';
import React,{useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import {useParams} from 'next/navigation';
import Link from 'next/link';
import {Boxes,PlusCircle,Sliders,AlertTriangle,History,Edit2,X,ArrowDownLeft,ArrowUpRight,CheckCircle2,RefreshCw} from 'lucide-react';
import {businessApi,Product,InventoryBalance,PurchaseRecord,SalesInvoice} from '../../../../lib/business-api';
import {addMoney,formatINR} from '../../../../lib/money';

export default function InventoryPage(){
	const {toast}=useToast();
	const params=useParams();
	const businessId=params.id as string;

	const [balances,setBalances]=useState<InventoryBalance[]>([]);
	const [products,setProducts]=useState<Product[]>([]);
	const [movements,setMovements]=useState<any[]>([]);
	const [purchases,setPurchases]=useState<PurchaseRecord[]>([]);
	const [invoices,setInvoices]=useState<SalesInvoice[]>([]);
	const [costReview,setCostReview]=useState<any>(null);
	const [reconcilingCosts,setReconcilingCosts]=useState(false);
	const [attestationMovementId,setAttestationMovementId]=useState('');
	const [attestationCost,setAttestationCost]=useState('');
	const [attestationNote,setAttestationNote]=useState('');
	const [loading,setLoading]=useState(true);
	const [mounted,setMounted]=useState(false);
	const [activeTab,setActiveTab]=useState<'BALANCES'|'MATRIX'|'MOVEMENTS'>('MATRIX');

	const [showAddProduct,setShowAddProduct]=useState(false);
	const [prodName,setProdName]=useState('');
	const [prodSku,setProdSku]=useState('');
	const [prodCategory,setProdCategory]=useState('RAW_MATERIALS');
	const [prodUnit,setProdUnit]=useState('KG');
	const [prodSellingPrice,setProdSellingPrice]=useState('100');
	const [prodPurchasePrice,setProdPurchasePrice]=useState('70');
	const [prodInitialStock,setProdInitialStock]=useState('0');
	const [prodReorderLevel,setProdReorderLevel]=useState('10');

	const [showAdjustModal,setShowAdjustModal]=useState(false);
	const [selectedProductId,setSelectedProductId]=useState('');
	const [deltaQuantity,setDeltaQuantity]=useState('');
	const [movementType,setMovementType]=useState('MANUAL_ADJUSTMENT');
	const [adjustmentNote,setAdjustmentNote]=useState('');

	const [editingProduct,setEditingProduct]=useState<Product|null>(null);
	const [editProdName,setEditProdName]=useState('');
	const [editProdCategory,setEditProdCategory]=useState('');
	const [editProdSellingPrice,setEditProdSellingPrice]=useState('');
	const [editProdPurchasePrice,setEditProdPurchasePrice]=useState('');
	const [editProdReorderLevel,setEditProdReorderLevel]=useState('');

	useEffect(()=>{
		setMounted(true);
	},[]);

	const loadAllData=async()=>{
		try{
			const [balList,prodList,movList,review,purchList,invList]=await Promise.all([
				businessApi.getInventoryBalances(businessId).catch(()=>[]),
				businessApi.listProducts(businessId).catch(()=>[]),
				businessApi.getInventoryMovements(businessId).catch(()=>[]),
				businessApi.getUnreconciledInventoryCosts(businessId).catch(()=>null),
				businessApi.listPurchases(businessId).catch(()=>[]),
				businessApi.listInvoices(businessId).catch(()=>[]),
			]);
			setBalances(balList);
			setProducts(prodList);
			setMovements(movList);
			setCostReview(review);
			setPurchases(purchList);
			setInvoices(invList);
		}catch(err){
			console.error('Failed to load inventory data',err);
		}finally{
			setLoading(false);
		}
	};

	useEffect(()=>{
		loadAllData();
	},[businessId]);

	const handleCreateProduct=async(e:React.FormEvent)=>{
		e.preventDefault();
		try{
			await businessApi.createProduct(businessId,{
				name:prodName,
				sku:prodSku||`SKU-${Date.now().toString().slice(-4)}`,
				category:prodCategory,
				unit_of_measure:prodUnit,
				selling_price_amount:prodSellingPrice,
				purchase_price_amount:prodPurchasePrice,
				current_stock:parseFloat(prodInitialStock)||0,
				reorder_level:parseFloat(prodReorderLevel)||0,
			});
			setShowAddProduct(false);
			setProdName('');
			setProdSku('');
			setProdInitialStock('0');
			setProdReorderLevel('10');
			toast.success('Product catalog item created');
			await loadAllData();
		}catch(err:any){
			toast.error(`Product creation failed: ${err.message}`);
		}
	};

	const handleAdjustInventory=async(e:React.FormEvent)=>{
		e.preventDefault();
		try{
			await businessApi.adjustInventory(businessId,{
				product_id:selectedProductId,
				quantity_delta:parseFloat(deltaQuantity),
				movement_type:'ADJUSTMENT',
				reference_note:`[${movementType}] ${adjustmentNote||'Quantity manual adjustment'}`,
			});
			setShowAdjustModal(false);
			setDeltaQuantity('');
			setAdjustmentNote('');
			toast.success('Inventory units successfully adjusted');
			await loadAllData();
		}catch(err:any){
			toast.error(`Quantity adjustment failed: ${err.message}`);
		}
	};

	const handleUpdateProduct=async(e:React.FormEvent)=>{
		e.preventDefault();
		if(!editingProduct)return;
		try{
			const updated=await businessApi.updateProduct(businessId,editingProduct.id,{
				name:editProdName,
				category:editProdCategory,
				selling_price_amount:editProdSellingPrice||'0.00',
				purchase_price_amount:editProdPurchasePrice||'0.00',
				reorder_level:parseFloat(editProdReorderLevel)||0,
			});
			setProducts((prev)=>prev.map((p)=>(p.id===editingProduct.id?{...p,...updated}:p)));
			setEditingProduct(null);
			const balList=await businessApi.getInventoryBalances(businessId);
			setBalances(balList);
			toast.success('Product details updated');
		}catch(err:any){
			toast.error(`Update failed: ${err.message}`);
		}
	};

	const totalInventoryValuation=balances.reduce(
		(total,balance)=>addMoney(total,balance.total_valuation||'0.00'),'0.00',
	);

	const formatCurrency=(val:number|string|undefined|null)=>{
		if(val===undefined||val===null)return '₹0.00';
		return formatINR(val);
	};

	const submitCostReconciliation=async(
		mode:'CHRONOLOGICAL_REPLAY'|'MANUAL_ATTESTATION',
		overrides:Array<{movement_id:string;unit_cost:string;note:string}>=[],
	)=>{
		setReconcilingCosts(true);
		try{
			const result=await businessApi.reconcileInventoryCosts(businessId,{mode,overrides});
			toast.success(`Cost reconciliation ${result.status.toLowerCase()}: ${result.resolved_movement_count} movement(s) resolved.`);
			await loadAllData();
			setAttestationMovementId('');
			setAttestationCost('');
			setAttestationNote('');
		}catch(error){
			toast.error(`Cost reconciliation failed: ${(error as Error).message}`);
		}finally{
			setReconcilingCosts(false);
		}
	};

	const getEntangledProductMetrics=(p:Product)=>{
		const pName=p.name.trim().toLowerCase();
		let totalPurchased=0;
		let purchaseBillsCount=0;
		purchases.forEach((pr)=>{
			(pr.items||[]).forEach((it:any)=>{
				const match=it.product_id===p.id||(it.description&&it.description.trim().toLowerCase()===pName);
				if(match){
					totalPurchased+=Number(it.quantity)||0;
					purchaseBillsCount++;
				}
			});
		});

		let totalSold=0;
		let salesInvoicesCount=0;
		invoices.forEach((inv)=>{
			(inv.items||[]).forEach((it:any)=>{
				const match=it.product_id===p.id||(it.description&&it.description.trim().toLowerCase()===pName);
				if(match){
					totalSold+=Number(it.quantity)||0;
					salesInvoicesCount++;
				}
			});
		});

		const bal=balances.find((b)=>b.product_id===p.id);
		const onHand=bal?Number(bal.current_stock):Number(p.current_stock)||0;
		const wac=bal?bal.weighted_average_cost:p.weighted_average_cost||p.purchase_price_amount||0;
		const valuation=bal?bal.total_valuation:Number(onHand)*Number(wac);

		return{
			totalPurchased,
			purchaseBillsCount,
			totalSold,
			salesInvoicesCount,
			onHand,
			wac,
			valuation,
			unit:p.unit_of_measure||'units',
		};
	};

	return(
		<div className="space-y-6 max-w-7xl mx-auto">
			<div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b-2 border-[#231412]">
				<div>
					<h1 className="text-2xl font-black text-[#231412] uppercase tracking-wide">Inventory & Units Ledger</h1>
					<p className="text-xs font-mono text-[#5C403B] mt-0.5">
						Unified Entangled Nexus: Real-time synchronization of Procurement Bills, Inventory Units, and Sales Invoices.
					</p>
				</div>

				<div className="flex flex-wrap items-center gap-2">
					<Link
						href={`/workspaces/${businessId}/purchases`}
						className="px-3 py-2 border-2 border-[#231412] bg-[#FAF7F2] text-[#231412] text-xs font-black uppercase tracking-wider hover:bg-white shadow-[2px_2px_0px_#231412] transition-all flex items-center space-x-1"
					>
						<ArrowDownLeft className="w-3.5 h-3.5 text-[#2E7D32]" />
						<span>+ Procure (Inward)</span>
					</Link>
					<Link
						href={`/workspaces/${businessId}/sales`}
						className="px-3 py-2 border-2 border-[#231412] bg-[#FAF7F2] text-[#231412] text-xs font-black uppercase tracking-wider hover:bg-white shadow-[2px_2px_0px_#231412] transition-all flex items-center space-x-1"
					>
						<ArrowUpRight className="w-3.5 h-3.5 text-[#C8281E]" />
						<span>+ Sell (Outward)</span>
					</Link>
					<MotionButton
						onClick={()=>setShowAdjustModal(true)}
						className="px-3 py-2 border-2 border-[#231412] bg-white text-[#231412] text-xs font-black uppercase tracking-wider hover:bg-[#FAF7F2] shadow-[2px_2px_0px_#231412] transition-all flex items-center space-x-1"
					>
						<Sliders className="w-3.5 h-3.5 text-[#231412]" />
						<span>Quantity Adjustment</span>
					</MotionButton>
					<MotionButton
						onClick={()=>setShowAddProduct(true)}
						className="px-3.5 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-black uppercase tracking-wider hover:bg-[#A61E14] shadow-[2px_2px_0px_#231412] transition-all flex items-center space-x-1"
					>
						<PlusCircle className="w-3.5 h-3.5 text-white" />
						<span>Add Product SKU</span>
					</MotionButton>
				</div>
			</div>

			<div className="p-4 bg-[#FAF7F2] border-2 border-[#231412] shadow-[4px_4px_0px_#231412]">
				<div className="flex flex-col md:flex-row items-center justify-between gap-4">
					<div className="flex items-center space-x-3">
						<div className="w-8 h-8 rounded-none border-2 border-[#231412] bg-[#C8281E] text-white flex items-center justify-center font-black text-xs shadow-[2px_2px_0px_#231412]">
							∞
						</div>
						<div>
							<div className="text-xs font-black uppercase text-[#231412] tracking-wider">
								Tri-Partite Entangled Flow Architecture
							</div>
							<div className="text-[11px] font-mono text-[#5C403B]">
								Purchases (+Inward Units) ➔ Stored Units on Hand (WAC) ➔ Sales Invoices (-Outward Units)
							</div>
						</div>
					</div>
					<div className="flex items-center gap-2">
						<button
							onClick={()=>setActiveTab('MATRIX')}
							className={`px-3 py-1.5 text-xs font-black uppercase tracking-wider border-2 border-[#231412] transition-all ${
								activeTab==='MATRIX'?'bg-[#C8281E] text-white shadow-[2px_2px_0px_#231412]':'bg-white text-[#231412] hover:bg-[#FAF7F2]'
							}`}
						>
							01 | Entangled Flow Matrix
						</button>
						<button
							onClick={()=>setActiveTab('BALANCES')}
							className={`px-3 py-1.5 text-xs font-black uppercase tracking-wider border-2 border-[#231412] transition-all ${
								activeTab==='BALANCES'?'bg-[#C8281E] text-white shadow-[2px_2px_0px_#231412]':'bg-white text-[#231412] hover:bg-[#FAF7F2]'
							}`}
						>
							02 | Master Units Ledger
						</button>
						<button
							onClick={()=>setActiveTab('MOVEMENTS')}
							className={`px-3 py-1.5 text-xs font-black uppercase tracking-wider border-2 border-[#231412] transition-all ${
								activeTab==='MOVEMENTS'?'bg-[#C8281E] text-white shadow-[2px_2px_0px_#231412]':'bg-white text-[#231412] hover:bg-[#FAF7F2]'
							}`}
						>
							03 | Immutable Audit Trail
						</button>
					</div>
				</div>
			</div>

			{costReview&&costReview.unreconciled_movement_count>0&&(
				<section className="space-y-4 border-2 border-[#D97706] bg-[#FAF7F2] p-5 shadow-[4px_4px_0px_#D97706]">
					<div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
						<div>
							<h2 className="flex items-center gap-2 text-sm font-black text-[#D97706] uppercase tracking-wide">
								<AlertTriangle className="h-4 w-4" /> Historical inventory costs need review
							</h2>
							<p className="mt-1 text-xs text-[#5C403B]">
								{costReview.unreconciled_movement_count} unresolved movement(s) across {costReview.unreconciled_product_count} product(s).
								Estimated COGS impact {formatCurrency(costReview.estimated_cogs_impact)}; estimates are informational and never posted.
							</p>
						</div>
						<MotionButton
							type="button"
							disabled={reconcilingCosts}
							onClick={()=>void submitCostReconciliation('CHRONOLOGICAL_REPLAY')}
							className="shrink-0 border-2 border-[#231412] bg-[#D97706] px-3 py-2 text-xs font-black uppercase tracking-wider text-white shadow-[2px_2px_0px_#231412] hover:bg-[#B45309] disabled:opacity-60"
						>
							{reconcilingCosts?'Reconciling…':'Replay verified sources'}
						</MotionButton>
					</div>
					<div className="overflow-x-auto border-2 border-[#231412] bg-white">
						<table className="w-full min-w-[700px] text-left text-xs">
							<thead>
								<tr className="border-b-2 border-[#231412] bg-[#FAF7F2] text-[#231412] uppercase font-black tracking-wider text-[11px]">
									<th className="p-3">Movement</th>
									<th className="p-3">Product</th>
									<th className="p-3 text-right">Quantity</th>
									<th className="p-3 text-right">Recorded basis</th>
									<th className="p-3 text-right">Estimated COGS</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-[#231412]/10">
								{(costReview.movements||[]).slice(0,10).map((row:any)=>(
									<tr key={row.movement_id} className="hover:bg-[#FAF7F2]/60">
										<td className="p-3">
											<div className="font-bold text-[#231412]">{row.movement_type}</div>
											<div className="text-[10px] font-mono text-[#5C403B]">{row.movement_date?new Date(row.movement_date).toLocaleDateString():'—'}</div>
										</td>
										<td className="p-3 font-medium text-[#231412]">{row.product_name}</td>
										<td className="p-3 text-right font-mono font-bold text-[#231412]">{row.quantity}</td>
										<td className="p-3 text-right font-mono text-[#5C403B]">{row.cost_basis?formatCurrency(row.cost_basis):'Unknown'}</td>
										<td className="p-3 text-right font-mono font-bold text-[#231412]">{row.estimated_cogs_impact?formatCurrency(row.estimated_cogs_impact):'—'}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
					<div className="grid gap-2 md:grid-cols-[1fr_150px_1fr_auto]">
						<select className="border-2 border-[#231412] bg-white px-3 py-2 text-xs font-mono text-[#231412] focus:outline-none" value={attestationMovementId} onChange={(event)=>setAttestationMovementId(event.target.value)}>
							<option value="">Select an opening/adjustment movement to attest</option>
							{(costReview.movements||[]).filter((row:any)=>['OPENING','ADJUSTMENT'].includes(row.movement_type)).map((row:any)=>(
								<option key={row.movement_id} value={row.movement_id}>{row.product_name} · {row.movement_type} · {row.quantity}</option>
							))}
						</select>
						<input aria-label="Attested unit cost" type="number" min="0" step="0.01" placeholder="Cost / unit ₹" className="border-2 border-[#231412] bg-white px-3 py-2 text-xs font-mono text-[#231412] focus:outline-none" value={attestationCost} onChange={(event)=>setAttestationCost(event.target.value)} />
						<input aria-label="Attestation evidence note" placeholder="Evidence note" className="border-2 border-[#231412] bg-white px-3 py-2 text-xs font-mono text-[#231412] focus:outline-none" value={attestationNote} onChange={(event)=>setAttestationNote(event.target.value)} />
						<MotionButton
							type="button"
							disabled={reconcilingCosts||!attestationMovementId||!attestationCost||attestationNote.trim().length<3}
							onClick={()=>void submitCostReconciliation('MANUAL_ATTESTATION',[{
								movement_id:attestationMovementId,unit_cost:attestationCost,note:attestationNote.trim(),
							}])}
							className="border-2 border-[#231412] bg-[#C8281E] px-3 py-2 text-xs font-black uppercase tracking-wider text-white shadow-[2px_2px_0px_#231412] hover:bg-[#A61E14] disabled:opacity-50"
						>
							Attest cost
						</MotionButton>
					</div>
				</section>
			)}

			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div className="p-4 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412]">
					<div className="text-[10px] font-bold text-[#5C403B] uppercase tracking-wider">Total Inventory Valuation (WAC)</div>
					<div className="text-2xl font-black font-mono text-[#231412] mt-1">{formatCurrency(totalInventoryValuation)}</div>
					<div className="text-[11px] font-mono text-[#5C403B] mt-1">Perpetual weighted average valuation</div>
				</div>
				<div className="p-4 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412]">
					<div className="text-[10px] font-bold text-[#5C403B] uppercase tracking-wider">Active Catalog SKUs</div>
					<div className="text-2xl font-black font-mono text-[#231412] mt-1">{products.length} Items</div>
					<div className="text-[11px] font-mono text-[#5C403B] mt-1">Synchronized across Purchases & Sales</div>
				</div>
				<div className="p-4 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412]">
					<div className="text-[10px] font-bold text-[#5C403B] uppercase tracking-wider">Reorder Alerts</div>
					<div className="text-2xl font-black font-mono text-[#C8281E] mt-1">
						{balances.filter((b)=>b.needs_reorder).length} Items Below Threshold
					</div>
					<div className="text-[11px] font-mono text-[#5C403B] mt-1">Requires procurement requisition</div>
				</div>
			</div>

			{activeTab==='MATRIX'&&(
				<div className="p-6 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412] space-y-4 animate-in fade-in-50">
					<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
						<div>
							<div className="text-sm font-black text-[#231412] uppercase tracking-wider">
								Continuous Entangled Reconciliation Matrix
							</div>
							<p className="text-xs font-mono text-[#5C403B]">
								Mathematical audit proof: Inward Purchases (+) minus Outward Sales (-) equals Units on Hand.
							</p>
						</div>
						<div className="px-2.5 py-1 border-2 border-[#2E7D32] bg-[#2E7D32]/10 text-[#2E7D32] text-xs font-bold uppercase inline-flex items-center space-x-1.5">
							<CheckCircle2 className="w-3.5 h-3.5 text-[#2E7D32]" />
							<span>Zero-Contradiction Verified</span>
						</div>
					</div>

					{products.length===0?(
						<div className="text-center py-10 text-xs font-mono text-[#5C403B]">
							No products in catalog. Add a product or record a purchase bill to view the entangled lifecycle matrix.
						</div>
					):(
						<div className="overflow-x-auto border-2 border-[#231412]">
							<table className="w-full text-left text-xs">
								<thead>
									<tr className="border-b-2 border-[#231412] bg-[#FAF7F2] text-[#231412] uppercase font-black tracking-wider text-[11px]">
										<th className="py-3 px-4">Product / SKU</th>
										<th className="py-3 px-4 text-center">Unit</th>
										<th className="py-3 px-4 text-right bg-[#2E7D32]/5 text-[#2E7D32]">Inward Procured (+)</th>
										<th className="py-3 px-4 text-right bg-[#C8281E]/5 text-[#C8281E]">Outward Invoiced (-)</th>
										<th className="py-3 px-4 text-right bg-[#231412]/5 font-black">Units On Hand</th>
										<th className="py-3 px-4 text-right">WAC Cost</th>
										<th className="py-3 px-4 text-right">Valuation</th>
										<th className="py-3 px-4 text-center">Status</th>
									</tr>
								</thead>
								<tbody className="divide-y divide-[#231412]/10">
									{products.map((p)=>{
										const m=getEntangledProductMetrics(p);
										return(
											<tr key={p.id} className="hover:bg-[#FAF7F2]/60">
												<td className="py-3 px-4">
													<div className="font-bold text-[#231412]">{p.name}</div>
													<div className="font-mono text-[10px] text-[#5C403B]">{p.sku}</div>
												</td>
												<td className="py-3 px-4 text-center font-mono text-[#5C403B]">{m.unit}</td>
												<td className="py-3 px-4 text-right font-mono font-bold text-[#2E7D32] bg-[#2E7D32]/5">
													+{m.totalPurchased}
													<span className="text-[10px] text-[#5C403B] block font-normal">({m.purchaseBillsCount} bills)</span>
												</td>
												<td className="py-3 px-4 text-right font-mono font-bold text-[#C8281E] bg-[#C8281E]/5">
													-{m.totalSold}
													<span className="text-[10px] text-[#5C403B] block font-normal">({m.salesInvoicesCount} invoices)</span>
												</td>
												<td className="py-3 px-4 text-right font-mono font-black text-[#231412] bg-[#231412]/5 text-sm">
													{m.onHand}
												</td>
												<td className="py-3 px-4 text-right font-mono font-medium text-[#5C403B]">
													{formatCurrency(m.wac)}
												</td>
												<td className="py-3 px-4 text-right font-mono font-black text-[#2E7D32]">
													{formatCurrency(m.valuation)}
												</td>
												<td className="py-3 px-4 text-center">
													<span className="px-2 py-0.5 border border-[#2E7D32] text-[10px] font-bold uppercase bg-[#2E7D32]/10 text-[#2E7D32]">
														Entangled
													</span>
												</td>
											</tr>
										);
									})}
								</tbody>
							</table>
						</div>
					)}
				</div>
			)}

			{activeTab==='BALANCES'&&(
				<div className="p-6 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412] space-y-4 animate-in fade-in-50">
					<div className="text-sm font-black text-[#231412] uppercase tracking-wider">Current Master Units On Hand & Valuation</div>
					{balances.length===0?(
						<div className="text-center py-10 text-xs font-mono text-[#5C403B]">
							No inventory items recorded yet. Click &ldquo;Add Product SKU&rdquo; to create your product catalog.
						</div>
					):(
						<div className="overflow-x-auto border-2 border-[#231412]">
							<table className="w-full text-left text-xs">
								<thead>
									<tr className="border-b-2 border-[#231412] bg-[#FAF7F2] text-[#231412] uppercase font-black tracking-wider text-[11px]">
										<th className="py-3 px-4">SKU</th>
										<th className="py-3 px-4">Product Name</th>
										<th className="py-3 px-4 text-center">Unit</th>
										<th className="py-3 px-4 text-right">Units on Hand</th>
										<th className="py-3 px-4 text-right">WAC Cost</th>
										<th className="py-3 px-4 text-right">Total Valuation</th>
										<th className="py-3 px-4 text-center">Reorder Status</th>
										<th className="py-3 px-4 text-center">Actions</th>
									</tr>
								</thead>
								<tbody className="divide-y divide-[#231412]/10">
									{balances.map((b)=>(
										<tr key={b.product_id} className="hover:bg-[#FAF7F2]/60">
											<td className="py-3 px-4 font-mono text-[#5C403B]">{b.sku}</td>
											<td className="py-3 px-4 font-bold text-[#231412]">{b.name}</td>
											<td className="py-3 px-4 text-center font-mono text-[#5C403B]">{b.unit_of_measure}</td>
											<td className="py-3 px-4 text-right font-mono font-black text-[#231412]">{b.current_stock}</td>
											<td className="py-3 px-4 text-right font-mono font-medium text-[#5C403B]">
												{formatCurrency(b.weighted_average_cost)}
											</td>
											<td className="py-3 px-4 text-right font-mono font-black text-[#2E7D32]">
												{formatCurrency(b.total_valuation)}
											</td>
											<td className="py-3 px-4 text-center">
												{b.needs_reorder?(
													<span className="px-2 py-0.5 border border-[#D97706] text-[10px] font-bold uppercase bg-[#D97706]/10 text-[#D97706] inline-flex items-center space-x-1">
														<AlertTriangle className="w-3 h-3 text-[#D97706]" />
														<span>Reorder Needed</span>
													</span>
												):(
													<span className="px-2 py-0.5 border border-[#2E7D32] text-[10px] font-bold uppercase bg-[#2E7D32]/10 text-[#2E7D32]">
														Sufficient
													</span>
												)}
											</td>
											<td className="py-3 px-4 text-center">
												<MotionButton
													onClick={()=>{
														const prod=products.find((p)=>p.id===b.product_id)||{
															id:b.product_id,
															business_id:businessId,
															sku:b.sku,
															name:b.name,
															category:'GENERAL',
															unit_of_measure:b.unit_of_measure,
															selling_price_amount:0,
															purchase_price_amount:b.weighted_average_cost||0,
															current_stock:b.current_stock,
															weighted_average_cost:b.weighted_average_cost||0,
															reorder_level:0,
															tax_rate_pct:0,
															is_active:true,
															created_at:new Date().toISOString(),
														};
														setEditingProduct(prod);
														setEditProdName(prod.name);
														setEditProdCategory(prod.category||'GENERAL');
														setEditProdSellingPrice(prod.selling_price_amount?.toString()||'0');
														setEditProdPurchasePrice(prod.purchase_price_amount?.toString()||'0');
														setEditProdReorderLevel(prod.reorder_level?.toString()||'0');
													}}
													className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#FAF7F2] shadow-[1px_1px_0px_#231412]"
													title="Edit Product Details"
												>
													<Edit2 className="w-3.5 h-3.5" />
												</MotionButton>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</div>
			)}

			{activeTab==='MOVEMENTS'&&(
				<div className="p-6 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412] space-y-4 animate-in fade-in-50">
					<div className="flex items-center space-x-2 text-sm font-black text-[#231412] uppercase tracking-wider">
						<History className="w-4 h-4 text-[#C8281E]" />
						<span>Immutable Inventory Movements</span>
					</div>
					{movements.length===0?(
						<div className="text-center py-6 text-xs font-mono text-[#5C403B]">
							No movement records logged yet. Invoices, purchases, and manual adjustments log here.
						</div>
					):(
						<div className="overflow-x-auto border-2 border-[#231412]">
							<table className="w-full text-left text-xs">
								<thead>
									<tr className="border-b-2 border-[#231412] bg-[#FAF7F2] text-[#231412] uppercase font-black tracking-wider text-[11px]">
										<th className="py-2.5 px-3">Date</th>
										<th className="py-2.5 px-3">Type</th>
										<th className="py-2.5 px-3 text-right">Delta Units</th>
										<th className="py-2.5 px-3 text-right">New Balance</th>
										<th className="py-2.5 px-3">Reference Note</th>
									</tr>
								</thead>
								<tbody className="divide-y divide-[#231412]/10">
									{movements.slice(0,15).map((m)=>(
										<tr key={m.id} className="hover:bg-[#FAF7F2]/60">
											<td className="py-2.5 px-3 font-mono text-[#5C403B]">
												{m.created_at?new Date(m.created_at).toLocaleDateString():'—'}
											</td>
											<td className="py-2.5 px-3 font-bold text-[#231412]">{m.movement_type}</td>
											<td
												className={`py-2.5 px-3 text-right font-mono font-black ${
													m.quantity_delta>0?'text-[#2E7D32]':'text-[#C8281E]'
												}`}
											>
												{m.quantity_delta>0?`+${m.quantity_delta}`:m.quantity_delta}
											</td>
											<td className="py-2.5 px-3 text-right font-mono font-bold text-[#231412]">{m.new_stock_balance}</td>
											<td className="py-2.5 px-3 font-mono text-[#5C403B]">{m.reference_note||'—'}</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</div>
			)}

			{mounted&&showAddProduct&&createPortal(
				<div className="fixed inset-0 z-[100] bg-[#231412]/50 backdrop-blur-sm overflow-y-auto p-4 sm:p-6 flex justify-center items-start sm:items-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 my-auto animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div>
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">Add Product SKU</h3>
								<p className="text-xs text-[#5C403B]">Register catalog item with initial pricing & units on hand.</p>
							</div>
							<button
								type="button"
								onClick={()=>setShowAddProduct(false)}
								className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleCreateProduct} className="space-y-3">
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Product Name</label>
								<input
									type="text"
									required
									placeholder="e.g. Premium Bread Flour"
									value={prodName}
									onChange={(e)=>setProdName(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>

							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">SKU Code</label>
									<input
										type="text"
										placeholder="e.g. RAW-FLOUR-01"
										value={prodSku}
										onChange={(e)=>setProdSku(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Unit of Measure</label>
									<select
										value={prodUnit}
										onChange={(e)=>setProdUnit(e.target.value)}
										className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									>
										<option value="KG">KG (Kilograms)</option>
										<option value="PIECES">Pieces / Units</option>
										<option value="LITRES">Litres</option>
										<option value="BOXES">Boxes</option>
										<option value="BAGS">Bags / Sacks</option>
										<option value="METRES">Metres</option>
										<option value="PACKS">Packs</option>
									</select>
								</div>
							</div>

							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Cost Price (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={prodPurchasePrice}
										onChange={(e)=>setProdPurchasePrice(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Selling Price (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={prodSellingPrice}
										onChange={(e)=>setProdSellingPrice(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
							</div>

							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Initial Units on Hand</label>
									<input
										type="number"
										step="any"
										value={prodInitialStock}
										onChange={(e)=>setProdInitialStock(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Minimum Units Threshold</label>
									<input
										type="number"
										step="any"
										value={prodReorderLevel}
										onChange={(e)=>setProdReorderLevel(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
							</div>

							<div className="flex items-center justify-end space-x-2 pt-4 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setShowAddProduct(false)}
									className="px-3.5 py-2 border-2 border-[#231412] bg-white text-[#231412] text-xs font-bold uppercase hover:bg-[#FAF7F2] shadow-[2px_2px_0px_#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-black uppercase tracking-wider hover:bg-[#A61E14] shadow-[2px_2px_0px_#231412]"
								>
									Save Product
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}

			{mounted&&showAdjustModal&&createPortal(
				<div className="fixed inset-0 z-[100] bg-[#231412]/50 backdrop-blur-sm overflow-y-auto p-4 sm:p-6 flex justify-center items-start sm:items-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 my-auto animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div>
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">Quantity Adjustment</h3>
								<p className="text-xs text-[#5C403B]">Post positive or negative inventory delta with audit reason.</p>
							</div>
							<button
								type="button"
								onClick={()=>setShowAdjustModal(false)}
								className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleAdjustInventory} className="space-y-3">
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Select Product</label>
								<select
									required
									value={selectedProductId}
									onChange={(e)=>setSelectedProductId(e.target.value)}
									className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								>
									<option value="">Choose item...</option>
									{products.map((p)=>(
										<option key={p.id} value={p.id}>
											{p.name} (Available: {p.current_stock} units)
										</option>
									))}
								</select>
							</div>

							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Delta Quantity (+/-)</label>
									<input
										type="number"
										step="0.01"
										required
										placeholder="e.g. 5 or -2"
										value={deltaQuantity}
										onChange={(e)=>setDeltaQuantity(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Adjustment Reason</label>
									<select
										value={movementType}
										onChange={(e)=>setMovementType(e.target.value)}
										className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									>
										<option value="MANUAL_ADJUSTMENT">Physical Audit Count</option>
										<option value="INWARD_UNITS">Inward Units (Bonus/Found)</option>
										<option value="OUTWARD_UNITS">Outward Units (Transfer)</option>
										<option value="DAMAGED">Damaged / Expired</option>
										<option value="THEFT_OR_LOSS">Theft / Unaccounted</option>
									</select>
								</div>
							</div>

							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Audit Reference Note</label>
								<input
									type="text"
									placeholder="e.g. Physical inventory count verified"
									value={adjustmentNote}
									onChange={(e)=>setAdjustmentNote(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>

							<div className="flex items-center justify-end space-x-2 pt-4 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setShowAdjustModal(false)}
									className="px-3.5 py-2 border-2 border-[#231412] bg-white text-[#231412] text-xs font-bold uppercase hover:bg-[#FAF7F2] shadow-[2px_2px_0px_#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-black uppercase tracking-wider hover:bg-[#A61E14] shadow-[2px_2px_0px_#231412]"
								>
									Record Adjustment
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}

			{mounted&&editingProduct&&createPortal(
				<div className="fixed inset-0 z-[100] bg-[#231412]/50 backdrop-blur-sm overflow-y-auto p-4 sm:p-6 flex justify-center items-start sm:items-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 my-auto animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div>
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">Edit Product SKU</h3>
								<p className="text-xs text-[#5C403B]">Update SKU naming, pricing matrix, and minimum units threshold.</p>
							</div>
							<button
								type="button"
								onClick={()=>setEditingProduct(null)}
								className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleUpdateProduct} className="space-y-3">
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Product Name</label>
								<input
									type="text"
									required
									value={editProdName}
									onChange={(e)=>setEditProdName(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Category</label>
								<input
									type="text"
									required
									value={editProdCategory}
									onChange={(e)=>setEditProdCategory(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Selling Price (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={editProdSellingPrice}
										onChange={(e)=>setEditProdSellingPrice(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Purchase Price (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={editProdPurchasePrice}
										onChange={(e)=>setEditProdPurchasePrice(e.target.value)}
										className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
							</div>
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Minimum Units Threshold</label>
								<input
									type="number"
									step="any"
									required
									value={editProdReorderLevel}
									onChange={(e)=>setEditProdReorderLevel(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] font-mono focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="flex items-center justify-end space-x-2 pt-4 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setEditingProduct(null)}
									className="px-3.5 py-2 border-2 border-[#231412] bg-white text-[#231412] text-xs font-bold uppercase hover:bg-[#FAF7F2] shadow-[2px_2px_0px_#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-black uppercase tracking-wider hover:bg-[#A61E14] shadow-[2px_2px_0px_#231412]"
								>
									Save Changes
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}
		</div>
	);
}
