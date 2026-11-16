'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {useToast} from '@/components/ui';
import React,{useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import {useParams} from 'next/navigation';
import {
	Plus,
	Trash2,
	FileDown,
	Edit2,
	X,
	Boxes,
} from 'lucide-react';
import {
	businessApi,
	PurchaseRecord,
	Supplier,
	Product,
	PurchaseItem,
	downloadAuthenticatedReport,
} from '../../../../lib/business-api';
import {addMoney,applyDiscountAndTax,formatINR,mulMoneyQty,toMinorUnits} from '../../../../lib/money';

function safeMoney(operation:()=>string):string{
	try{return operation();}catch{return '0.00';}
}

function lineSubtotal(item:PurchaseItem):string{
	return safeMoney(()=>mulMoneyQty(item.unit_price,item.quantity));
}

function lineTax(item:PurchaseItem):string{
	return safeMoney(()=>applyDiscountAndTax(
		lineSubtotal(item),'0',item.tax_rate_pct??'18',
	).tax);
}

const STANDARD_PROCUREMENT_ITEMS=[
	{id:'pur-raw-material',name:'Industrial Raw Material Supply Lot',unit_price:'3200',tax_rate_pct:'12'},
	{id:'pur-machined-parts',name:'CNC Machined Component Castings',unit_price:'4500',tax_rate_pct:'18'},
	{id:'pur-hardware-kit',name:'Fasteners & Structural Hardware Kit',unit_price:'1200',tax_rate_pct:'18'},
	{id:'pur-electronic-ics',name:'Control Board & Microcontroller ICs',unit_price:'1850',tax_rate_pct:'18'},
	{id:'pur-freight-inward',name:'Inward Logistics, Freight & Packaging',unit_price:'850',tax_rate_pct:'5'},
	{id:'pur-packaging',name:'Corrugated Shipping Boxes & Crates',unit_price:'450',tax_rate_pct:'12'},
];

export default function PurchasesPage(){
	const {toast}=useToast();
	const params=useParams();
	const businessId=params.id as string;

	const [purchases,setPurchases]=useState<PurchaseRecord[]>([]);
	const [suppliers,setSuppliers]=useState<Supplier[]>([]);
	const [products,setProducts]=useState<Product[]>([]);
	const [loading,setLoading]=useState(true);

	const [showCreateModal,setShowCreateModal]=useState(false);
	const [editingPurchase,setEditingPurchase]=useState<PurchaseRecord|null>(null);
	const [selectedSupplierId,setSelectedSupplierId]=useState('');
	const [supplierName,setSupplierName]=useState('');
	const [supplierPhone,setSupplierPhone]=useState('');
	const [purchaseDate,setPurchaseDate]=useState(new Date().toISOString().split('T')[0]);
	const [dueDate,setDueDate]=useState('');
	const [poNumber,setPoNumber]=useState('');
	const [lineItems,setLineItems]=useState<PurchaseItem[]>([
		{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'},
	]);
	const [isCashPurchase,setIsCashPurchase]=useState(false);

	const [showPaymentModal,setShowPaymentModal]=useState(false);
	const [activePurchase,setActivePurchase]=useState<PurchaseRecord|null>(null);
	const [paymentAmount,setPaymentAmount]=useState('');
	const [paymentMethod,setPaymentMethod]=useState('BANK_TRANSFER');

	const [showQuickAddModal,setShowQuickAddModal]=useState(false);
	const [quickAddTargetIndex,setQuickAddTargetIndex]=useState<number|null>(null);
	const [quickProdName,setQuickProdName]=useState('');
	const [quickProdSku,setQuickProdSku]=useState('');
	const [quickProdCategory,setQuickProdCategory]=useState('RAW_MATERIALS');
	const [quickProdPrice,setQuickProdPrice]=useState('1000');
	const [quickProdCost,setQuickProdCost]=useState('600');
	const [quickProdStock,setQuickProdStock]=useState('10');
	const [savingQuickProduct,setSavingQuickProduct]=useState(false);
	const [mounted,setMounted]=useState(false);

	useEffect(()=>{
		setMounted(true);
	},[]);

	useEffect(()=>{
		async function loadData(){
			try{
				const [purList,suppList,prodList]=await Promise.all([
					businessApi.listPurchases(businessId).catch(()=>[]),
					businessApi.listSuppliers(businessId).catch(()=>[]),
					businessApi.listProducts(businessId).catch(()=>[]),
				]);
				setPurchases(purList);
				setSuppliers(suppList);
				setProducts(prodList);
			}catch(err){
				console.error('Failed to load purchases data',err);
			}finally{
				setLoading(false);
			}
		}
		loadData();
	},[businessId]);

	const handleDescriptionChange=(index:number,text:string)=>{
		const updated=[...lineItems];
		const matchedProduct=products.find((p)=>p.name.toLowerCase()===text.trim().toLowerCase());
		const matchedStd=STANDARD_PROCUREMENT_ITEMS.find((s)=>s.name.toLowerCase()===text.trim().toLowerCase());
		if(matchedProduct){
			updated[index]={
				...updated[index],
				item_description:text,
				product_id:matchedProduct.id,
				unit_price:updated[index].unit_price==='0'||!updated[index].unit_price?String(matchedProduct.purchase_price_amount||matchedProduct.weighted_average_cost||0):updated[index].unit_price,
				tax_rate_pct:matchedProduct.tax_rate_pct||'18',
			};
		}else if(matchedStd){
			updated[index]={
				...updated[index],
				item_description:text,
				product_id:null,
				unit_price:updated[index].unit_price==='0'||!updated[index].unit_price?matchedStd.unit_price:updated[index].unit_price,
				tax_rate_pct:matchedStd.tax_rate_pct,
			};
		}else{
			updated[index]={
				...updated[index],
				item_description:text,
				product_id:null,
			};
		}
		setLineItems(updated);
	};

	const updateLineItem=(index:number,field:keyof PurchaseItem,val:any)=>{
		const updated=[...lineItems];
		updated[index]={...updated[index],[field]:val};
		setLineItems(updated);
	};

	const addLineItem=()=>{
		setLineItems([...lineItems,{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'}]);
	};

	const removeLineItem=(index:number)=>{
		if(lineItems.length<=1)return;
		setLineItems(lineItems.filter((_,i)=>i!==index));
	};

	const calculateSubtotal=()=>lineItems.reduce(
		(total,item)=>safeMoney(()=>addMoney(total,lineSubtotal(item))),'0.00',
	);

	const calculateTax=()=>lineItems.reduce(
		(total,item)=>safeMoney(()=>addMoney(total,lineTax(item))),'0.00',
	);

	const calculateTotal=()=>safeMoney(()=>addMoney(calculateSubtotal(),calculateTax()));

	const handleSupplierNameChange=(name:string)=>{
		setSupplierName(name);
		const match=suppliers.find((s)=>s.name.trim().toLowerCase()===name.trim().toLowerCase());
		if(match){
			setSelectedSupplierId(match.id);
			if(match.phone)setSupplierPhone(match.phone);
		}else if(name.trim().toLowerCase().includes('spot')||name.trim().toLowerCase().includes('cash')){
			setSelectedSupplierId('');
		}
	};

	const handleStartCreate=()=>{
		setEditingPurchase(null);
		setSelectedSupplierId('');
		setSupplierName('');
		setSupplierPhone('');
		setIsCashPurchase(false);
		setPurchaseDate(new Date().toISOString().split('T')[0]);
		setDueDate('');
		setPoNumber(`PO-${Date.now().toString().slice(-6)}`);
		setLineItems([{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'}]);
		setShowCreateModal(true);
	};

	const handleStartEdit=(p:PurchaseRecord)=>{
		setEditingPurchase(p);
		setSelectedSupplierId(p.supplier_id||'');
		const existingSupp=suppliers.find((s)=>s.id===p.supplier_id);
		let phone='';
		let name=existingSupp?existingSupp.name:'';
		if(existingSupp&&existingSupp.phone)phone=existingSupp.phone;
		if(!name&&!p.supplier_id)name='Spot / Cash Vendor';
		setSupplierName(name);
		setSupplierPhone(phone);
		setPurchaseDate(p.purchase_date);
		setDueDate(p.due_date||'');
		setPoNumber(p.purchase_order_number||p.id.slice(0,8));
		setLineItems(
			p.items&&p.items.length>0
				?p.items.map((it)=>({
					product_id:it.product_id,
					item_description:it.item_description,
					quantity:String(it.quantity),
					unit_price:String(it.unit_price),
					tax_rate_pct:it.tax_rate_pct||'18',
				}))
				:[{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'}]
		);
		setShowCreateModal(true);
	};

	const handleSavePurchase=async(e:React.FormEvent)=>{
		e.preventDefault();
		try{
			let suppId=selectedSupplierId||null;
			const trimmedName=supplierName.trim();
			const trimmedPhone=supplierPhone.trim();
			if(trimmedName&&!trimmedName.toLowerCase().includes('spot')&&!trimmedName.toLowerCase().includes('cash')){
				const match=suppliers.find((s)=>s.name.trim().toLowerCase()===trimmedName.toLowerCase());
				if(match){
					suppId=match.id;
					if(trimmedPhone&&match.phone!==trimmedPhone){
						try{
							await businessApi.updateSupplier(businessId,match.id,{phone:trimmedPhone});
						}catch{}
					}
				}else{
					try{
						const createdSupp=await businessApi.createSupplier(businessId,{
							name:trimmedName,
							phone:trimmedPhone,
						});
						suppId=createdSupp.id;
						setSuppliers((prev)=>[...prev,createdSupp]);
					}catch{}
				}
			}

			const processedItems = [...lineItems];
			for(let i=0; i<processedItems.length; i++){
				const item = processedItems[i];
				const desc = item.item_description.trim();
				if(!item.product_id && desc){
					const existingProd = products.find((p)=>p.name.trim().toLowerCase()===desc.toLowerCase());
					if(existingProd){
						processedItems[i] = { ...item, product_id: existingProd.id };
					}else{
						try{
							const autoSku = `MAT-${desc.slice(0,3).toUpperCase()}-${Date.now().toString().slice(-4)}`;
							const createdProd = await businessApi.createProduct(businessId,{
								name: desc,
								sku: autoSku,
								category: 'RAW_MATERIALS',
								selling_price_amount: String(Number(item.unit_price)*1.3),
								purchase_price_amount: item.unit_price,
								current_stock: 0,
								tax_rate_pct: Number(item.tax_rate_pct)||18,
							});
							setProducts((prev)=>[...prev,createdProd]);
							processedItems[i] = { ...item, product_id: createdProd.id };
						}catch{}
					}
				}
			}

			if(editingPurchase){
				const updated=await businessApi.updatePurchase(businessId,editingPurchase.id,{
					supplier_id:suppId,
					purchase_order_number:poNumber||editingPurchase.purchase_order_number||undefined,
					purchase_date:purchaseDate,
					due_date:dueDate||purchaseDate,
					items:processedItems,
					tax_amount:calculateTax(),
				});
				setPurchases(purchases.map((p)=>(p.id===updated.id?updated:p)));
				setShowCreateModal(false);
				setEditingPurchase(null);
				toast.success(`Purchase bill ${updated.purchase_order_number||updated.id.slice(0,8)} successfully updated!`);
				if(typeof window!=='undefined'){
					window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
				}
			}else{
				const created=await businessApi.createPurchase(businessId,{
					supplier_id:suppId,
					purchase_order_number:poNumber||undefined,
					purchase_date:purchaseDate,
					due_date:dueDate||purchaseDate,
					items:processedItems,
					tax_amount:calculateTax(),
					is_cash_purchase:isCashPurchase,
					immediate_payment_method:isCashPurchase?'CASH':undefined,
				});
				setPurchases([created,...purchases]);
				setShowCreateModal(false);
				setLineItems([{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'}]);
				toast.success(`Purchase bill ${created.purchase_order_number||created.id.slice(0,8)} recorded!`);
				if(typeof window!=='undefined'){
					window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
				}
			}
		}catch(err:any){
			toast.error(`Procurement processing failed: ${err.message}`);
		}
	};

	const handleDeletePurchase=async(purchaseId:string,billNumber:string)=>{
		if(!window.confirm(`Are you sure you want to delete purchase bill #${billNumber}? This will reverse inventory units and vendor payables.`))return;
		try{
			await businessApi.deletePurchase(businessId,purchaseId);
			setPurchases(purchases.filter((p)=>p.id!==purchaseId));
			toast.success(`Purchase bill #${billNumber} successfully deleted.`);
			if(typeof window!=='undefined'){
				window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
			}
		}catch(err:any){
			toast.error(`Delete failed: ${err.message}`);
		}
	};

	const handleRecordPayment=async(e:React.FormEvent)=>{
		e.preventDefault();
		if(!activePurchase)return;
		try{
			const updated=await businessApi.recordPurchasePayment(businessId,activePurchase.id,{
				amount:paymentAmount,
				payment_method:paymentMethod,
			});
			setPurchases(purchases.map((p)=>(p.id===updated.id?updated:p)));
			setShowPaymentModal(false);
			setActivePurchase(null);
			setPaymentAmount('');
			toast.success(`Settlement payment recorded on PO #${activePurchase.purchase_order_number||activePurchase.id.slice(0,8)}!`);
			if(typeof window!=='undefined'){
				window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
			}
		}catch(err:any){
			toast.error(`Purchase payment failed: ${err.message}`);
		}
	};

	const handleCreateQuickProduct=async(e:React.FormEvent)=>{
		e.preventDefault();
		if(!quickProdName.trim())return;
		setSavingQuickProduct(true);
		try{
			const generatedSku=quickProdSku.trim()||`SKU-${quickProdName.trim().slice(0,3).toUpperCase()}-${Date.now().toString().slice(-4)}`;
			const created=await businessApi.createProduct(businessId,{
				name:quickProdName.trim(),
				sku:generatedSku,
				category:quickProdCategory,
				selling_price_amount:quickProdPrice,
				purchase_price_amount:quickProdCost,
				current_stock:Number(quickProdStock)||0,
				tax_rate_pct:18,
			});
			setProducts((prev)=>[...prev,created]);
			if(quickAddTargetIndex!==null&&quickAddTargetIndex<lineItems.length){
				const updated=[...lineItems];
				updated[quickAddTargetIndex]={
					...updated[quickAddTargetIndex],
					item_description:created.name,
					product_id:created.id,
					unit_price:String(created.purchase_price_amount||quickProdCost),
					tax_rate_pct:'18',
				};
				setLineItems(updated);
			}
			setShowQuickAddModal(false);
			setQuickProdName('');
			setQuickProdSku('');
			toast.success(`Product "${created.name}" created and added to line items!`);
		}catch(err:any){
			toast.error(`Failed to register raw material: ${err.message}`);
		}finally{
			setSavingQuickProduct(false);
		}
	};

	const formatCurrency=(val:number|string|undefined|null)=>{
		if(val===undefined||val===null)return '₹0.00';
		return formatINR(val);
	};

	return(
		<div className="space-y-6 max-w-7xl mx-auto">
			<datalist id="procurement-catalog-suggestions">
				{products.map((p)=>(
					<option key={p.id} value={p.name}>{`Cost: ₹${p.purchase_price_amount||p.weighted_average_cost} | Available: ${p.current_stock} units`}</option>
				))}
				{STANDARD_PROCUREMENT_ITEMS.map((s)=>(
					<option key={s.id} value={s.name}>{`Cost: ₹${s.unit_price} | Standard Material`}</option>
				))}
			</datalist>

			<div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b-2 border-[#231412]">
				<div>
					<h1 className="text-2xl font-black text-[#231412] uppercase tracking-wide">Purchases & Procurement</h1>
					<p className="text-xs font-mono text-[#5C403B] mt-0.5">
						Vendor procurement bills, automated inventory valuation updates (WAC), and accounts payable.
					</p>
				</div>

				<MotionButton
					onClick={handleStartCreate}
					className="px-4 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-mono font-bold shadow-[3px_3px_0px_#231412] hover:bg-[#a51f17] transition-all flex items-center gap-1.5"
				>
					<Plus size={16} />
					<span>Record Purchase Bill</span>
				</MotionButton>
			</div>

			<div className="p-6 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412]">
				{purchases.length===0?(
					<div className="text-center py-12 text-xs font-mono text-[#5C403B]">
						No purchase bills recorded yet. Click &ldquo;Record Purchase Bill&rdquo; to inward inventory.
					</div>
				):(
					<div className="overflow-x-auto">
						<table className="w-full text-left text-xs font-mono">
							<thead>
								<tr className="border-b-2 border-[#231412] text-[#231412] uppercase font-bold text-[11px]">
									<th className="py-3 px-4">PO / Bill #</th>
									<th className="py-3 px-4">Date</th>
									<th className="py-3 px-4">Due Date</th>
									<th className="py-3 px-4 text-right">Total Amount</th>
									<th className="py-3 px-4 text-right">Outstanding</th>
									<th className="py-3 px-4 text-center">Status</th>
									<th className="py-3 px-4 text-center">Actions</th>
								</tr>
							</thead>
							<tbody className="divide-y border-b border-[#231412]/15">
								{purchases.map((p)=>(
									<tr key={p.id} className="hover:bg-[#FAF7F2]">
										<td className="py-3 px-4 font-bold text-[#231412]">
											{p.purchase_order_number||p.id.slice(0,8)}
										</td>
										<td className="py-3 px-4 text-[#5C403B]">{p.purchase_date}</td>
										<td className="py-3 px-4 text-[#5C403B]">{p.due_date||'—'}</td>
										<td className="py-3 px-4 text-right font-bold text-[#231412]">
											{formatCurrency(p.total_amount)}
										</td>
										<td className="py-3 px-4 text-right font-bold text-[#C8281E]">
											{formatCurrency(p.outstanding_amount)}
										</td>
										<td className="py-3 px-4 text-center">
											<span
												className={`px-2 py-0.5 border text-[10px] font-bold ${
													p.status==='PAID'
														?'bg-[#10B981]/15 text-[#10B981] border-[#10B981]'
														:p.status==='PARTIALLY_PAID'
														?'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]'
														:p.status==='CANCELLED'
														?'bg-[#231412]/10 text-[#5C403B] border-[#231412]/30'
														:'bg-[#C8281E]/15 text-[#C8281E] border-[#C8281E]'
												}`}
											>
												{p.status}
											</span>
										</td>
										<td className="py-3 px-4 text-center">
											<div className="flex items-center justify-center gap-1.5">
												{toMinorUnits(p.outstanding_amount)>BigInt(0)&&p.status!=='CANCELLED'&&(
													<MotionButton
														onClick={()=>{
															setActivePurchase(p);
															setPaymentAmount(String(p.outstanding_amount));
															setShowPaymentModal(true);
														}}
														className="px-2 py-1 border border-[#231412] bg-[#FAF7F2] text-[#231412] hover:bg-[#C8281E] hover:text-white text-[10px] font-mono font-bold transition-all shadow-[1px_1px_0px_#231412]"
													>
														Settle Bill
													</MotionButton>
												)}
												{p.status!=='CANCELLED'&&(
													<MotionButton
														type="button"
														onClick={()=>handleStartEdit(p)}
														title="Edit Purchase Bill"
														className="p-1 border border-[#231412]/30 text-[#231412] hover:bg-[#FAF7F2] hover:border-[#231412] hover:text-[#C8281E] transition-colors inline-flex items-center"
													>
														<Edit2 className="w-3.5 h-3.5" />
													</MotionButton>
												)}
												<MotionButton
													type="button"
													onClick={()=>handleDeletePurchase(p.id,p.purchase_order_number||p.id.slice(0,8))}
													title="Delete Purchase Bill"
													className="p-1 border border-[#231412]/30 text-[#231412] hover:bg-[#C8281E] hover:text-white hover:border-[#C8281E] transition-colors inline-flex items-center"
												>
													<Trash2 className="w-3.5 h-3.5" />
												</MotionButton>
												<MotionButton
													type="button"
													onClick={()=>downloadAuthenticatedReport(
														businessApi.getPurchasePdfUrl(businessId,p.id),
														`purchase-bill-${p.purchase_order_number||p.id.slice(0,8)}.pdf`,
													).catch((err:Error)=>toast.error(`PDF download failed: ${err.message}`))}
													title="Download Camera-Ready Purchase Bill PDF"
													className="p-1 border border-[#231412]/30 text-[#231412] hover:bg-[#FAF7F2] hover:border-[#231412] transition-colors inline-flex items-center"
												>
													<FileDown className="w-3.5 h-3.5 text-[#231412]" />
												</MotionButton>
											</div>
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</div>

			{mounted&&showCreateModal&&createPortal(
				<div className="fixed inset-0 z-[100] bg-[#231412]/50 backdrop-blur-sm overflow-y-auto p-4 sm:p-6 flex justify-center items-start sm:items-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-3xl w-full p-6 my-auto max-h-[92vh] flex flex-col animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] shrink-0 mb-4">
							<div>
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">
									{editingPurchase?`Edit Purchase Bill #${editingPurchase.purchase_order_number||editingPurchase.id.slice(0,8)}`:'Record Procurement Bill'}
								</h3>
								<p className="text-xs text-[#5C403B]">Inventory units on hand will increment and Weighted Average Cost will automatically recompute.</p>
							</div>
							<button
								type="button"
								onClick={()=>setShowCreateModal(false)}
								className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleSavePurchase} className="flex flex-col flex-1 min-h-0">
							<div className="overflow-y-auto flex-1 pr-1 space-y-4">
								<div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 bg-white border-2 border-[#231412]/20">
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
											Supplier Name (Write directly)
										</label>
										<input
											type="text"
											list="suppliers-catalog-suggestions"
											placeholder="Write vendor or supplier name..."
											value={supplierName}
											onChange={(e)=>handleSupplierNameChange(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
										<datalist id="suppliers-catalog-suggestions">
											<option value="Spot / Cash Vendor" />
											{suppliers.map((s)=>(
												<option key={s.id} value={s.name}>
													{s.phone?`${s.name} (${s.phone})`:s.name}
												</option>
											))}
										</datalist>
									</div>
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
											Supplier Mobile / Phone
										</label>
										<input
											type="tel"
											placeholder="+91 98450 99887"
											value={supplierPhone}
											onChange={(e)=>setSupplierPhone(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
											PO / Bill Ref #
										</label>
										<input
											type="text"
											required
											placeholder="e.g. PO-2026-001"
											value={poNumber}
											onChange={(e)=>setPoNumber(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
									<div className="md:col-span-1">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">Bill Date</label>
										<input
											type="date"
											required
											value={purchaseDate}
											onChange={(e)=>setPurchaseDate(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
									<div className="md:col-span-1">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">Due Date</label>
										<input
											type="date"
											value={dueDate}
											onChange={(e)=>setDueDate(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
								</div>

								{!editingPurchase&&(
									<div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-white border-2 border-[#231412]/20">
										<div>
											<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
												Settlement Terms
											</label>
											<div className="flex border-2 border-[#231412]">
												<button
													type="button"
													onClick={()=>setIsCashPurchase(false)}
													className={`flex-1 py-1.5 text-xs font-mono font-bold uppercase transition-all ${!isCashPurchase?'bg-[#231412] text-white':'bg-[#FAF7F2] text-[#231412]'}`}
												>
													Credit (Payable)
												</button>
												<div className="w-0.5 bg-[#231412]" />
												<button
													type="button"
													onClick={()=>setIsCashPurchase(true)}
													className={`flex-1 py-1.5 text-xs font-mono font-bold uppercase transition-all ${isCashPurchase?'bg-[#C8281E] text-white':'bg-[#FAF7F2] text-[#231412]'}`}
												>
													Cash (Immediate Outflow)
												</button>
											</div>
										</div>
										<div className="flex flex-col justify-center">
											<span className="text-[10px] font-mono text-[#5C403B]">
												{isCashPurchase?'Immediate Cash Purchase: deducts payment directly from Liquid Cash.':'Credit Procurement: records bill into Accounts Payable until settlement.'}
											</span>
										</div>
									</div>
								)}

								<div className="border-2 border-[#231412]/20 p-3 bg-white space-y-3">
									<div className="flex items-center justify-between pb-1 border-b border-[#231412]/15">
										<span className="text-xs font-mono font-bold text-[#231412] uppercase tracking-wider">
											Procurement Line Items ({lineItems.length})
										</span>
										<button
											type="button"
											onClick={()=>{
												setQuickAddTargetIndex(lineItems.length-1);
												setShowQuickAddModal(true);
											}}
											className="text-[11px] font-mono text-[#C8281E] hover:underline font-bold"
										>
											+ Quick Add Raw Material to Inventory
										</button>
									</div>

									<div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
										{lineItems.map((item,idx)=>(
											<div key={idx} className="grid grid-cols-12 gap-2 items-end p-2.5 bg-[#FAF7F2] border-2 border-[#231412]/15">
												<div className="col-span-5">
													<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase mb-1">
														Material / Item (Write directly)
													</label>
													<input
														type="text"
														required
														list="procurement-catalog-suggestions"
														value={item.item_description}
														onChange={(e)=>handleDescriptionChange(idx,e.target.value)}
														placeholder="Write material, part, or supply name..."
														className="w-full text-xs h-9 px-3 border-2 border-[#231412] bg-white font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
													/>
												</div>
												<div className="col-span-2">
													<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase mb-1">
														Qty
													</label>
													<input
														type="number"
														min="0.0001"
														step="any"
														required
														value={item.quantity}
														onChange={(e)=>updateLineItem(idx,'quantity',e.target.value)}
														className="w-full text-xs h-9 px-2.5 border-2 border-[#231412] bg-white font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
													/>
												</div>
												<div className="col-span-2">
													<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase mb-1">
														Unit Cost (₹)
													</label>
													<input
														type="number"
														step="0.01"
														required
														value={item.unit_price}
														onChange={(e)=>updateLineItem(idx,'unit_price',e.target.value)}
														className="w-full text-xs h-9 px-2.5 border-2 border-[#231412] bg-white font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
													/>
												</div>
												<div className="col-span-2">
													<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase mb-1">
														GST Rate
													</label>
													<select
														value={item.tax_rate_pct||'18'}
														onChange={(e)=>updateLineItem(idx,'tax_rate_pct',e.target.value)}
														className="w-full text-xs h-9 px-1.5 border-2 border-[#231412] bg-white font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
													>
														<option value="18">18% (Standard GST)</option>
														<option value="12">12% (Raw Material / Castings)</option>
														<option value="5">5% (Logistics / Packaging)</option>
														<option value="0">0% (Nil / Exempt)</option>
														<option value="28">28% (Special Industrial)</option>
													</select>
												</div>
												<div className="col-span-1 text-center pb-1">
													<button
														type="button"
														onClick={()=>removeLineItem(idx)}
														disabled={lineItems.length<=1}
														className="p-1.5 text-[#231412]/60 hover:text-[#C8281E] disabled:opacity-30 disabled:hover:text-[#231412]/60 transition-colors"
														title="Delete Item"
													>
														<Trash2 className="w-4 h-4 mx-auto" />
													</button>
												</div>
											</div>
										))}
									</div>

									<MotionButton
										type="button"
										onClick={addLineItem}
										className="inline-flex items-center gap-1.5 px-3 py-1.5 border-2 border-[#231412] bg-[#FAF7F2] text-xs font-mono font-bold text-[#231412] hover:bg-[#231412] hover:text-white transition-all shadow-[2px_2px_0px_#231412]"
									>
										<Plus size={14} /> Add Another Item
									</MotionButton>
								</div>

								<div className="bg-white p-3 border-2 border-[#231412]/20 space-y-1.5 text-xs font-mono">
									<div className="flex justify-between text-[#5C403B]">
										<span>Taxable Subtotal:</span>
										<span className="font-bold">{formatCurrency(calculateSubtotal())}</span>
									</div>
									<div className="flex justify-between text-[#5C403B]">
										<span>Central Tax (Input CGST @ 9%):</span>
										<span>{formatCurrency(Number(calculateTax())/2)}</span>
									</div>
									<div className="flex justify-between text-[#5C403B]">
										<span>State Tax (Input SGST @ 9%):</span>
										<span>{formatCurrency(Number(calculateTax())/2)}</span>
									</div>
									<div className="flex justify-between text-[#5C403B] font-bold">
										<span>Total Input Tax (GST):</span>
										<span>{formatCurrency(calculateTax())}</span>
									</div>
									<div className="flex justify-between font-black text-[#231412] text-sm pt-2 border-t-2 border-[#231412]/20">
										<span>Grand Total:</span>
										<span className="text-[#C8281E]">{formatCurrency(calculateTotal())}</span>
									</div>
								</div>
							</div>

							<div className="flex items-center justify-end gap-3 pt-4 border-t-2 border-[#231412] shrink-0 mt-4">
								<MotionButton
									type="button"
									onClick={()=>setShowCreateModal(false)}
									className="px-4 py-2 border-2 border-[#231412] bg-[#FAF7F2] text-xs font-mono font-bold text-[#231412] hover:bg-[#231412] hover:text-white transition-all"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-5 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-mono font-bold hover:bg-[#a51f17] transition-all shadow-[3px_3px_0px_#231412]"
								>
									{editingPurchase?'Update Bill':'Save Bill'}
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}

			{mounted&&showQuickAddModal&&createPortal(
				<div className="fixed inset-0 z-[110] bg-[#231412]/60 backdrop-blur-sm p-4 flex items-center justify-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div className="flex items-center gap-2">
								<Boxes className="w-5 h-5 text-[#C8281E]" />
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">Quick Add Material</h3>
							</div>
							<button
								type="button"
								onClick={()=>setShowQuickAddModal(false)}
								className="p-1 border border-[#231412] hover:bg-[#C8281E] hover:text-white transition-colors"
							>
								<X size={14} />
							</button>
						</div>

						<form onSubmit={handleCreateQuickProduct} className="space-y-3 font-mono text-xs">
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Material / Product Name *</label>
								<input
									type="text"
									required
									placeholder="e.g. Aircraft Grade Aluminium Alloy Billet"
									value={quickProdName}
									onChange={(e)=>setQuickProdName(e.target.value)}
									className="w-full h-8 px-2.5 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="grid grid-cols-2 gap-2">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">SKU / Code</label>
									<input
										type="text"
										placeholder="Auto-generated if blank"
										value={quickProdSku}
										onChange={(e)=>setQuickProdSku(e.target.value)}
										className="w-full h-8 px-2.5 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Category</label>
									<select
										value={quickProdCategory}
										onChange={(e)=>setQuickProdCategory(e.target.value)}
										className="w-full h-8 px-2 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									>
										<option value="RAW_MATERIALS">Raw Materials</option>
										<option value="COMPONENTS">Components</option>
										<option value="FINISHED_GOODS">Finished Goods</option>
										<option value="PACKAGING">Packaging</option>
										<option value="SERVICES">Services</option>
									</select>
								</div>
							</div>
							<div className="grid grid-cols-3 gap-2">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Purchase Cost (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={quickProdCost}
										onChange={(e)=>setQuickProdCost(e.target.value)}
										className="w-full h-8 px-2.5 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Selling Price (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={quickProdPrice}
										onChange={(e)=>setQuickProdPrice(e.target.value)}
										className="w-full h-8 px-2.5 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Initial Qty</label>
									<input
										type="number"
										step="any"
										value={quickProdStock}
										onChange={(e)=>setQuickProdStock(e.target.value)}
										className="w-full h-8 px-2.5 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
							</div>

							<div className="flex items-center justify-end gap-2 pt-3 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setShowQuickAddModal(false)}
									className="px-3 py-1.5 border border-[#231412] bg-[#FAF7F2] text-[#231412] text-xs font-bold hover:bg-[#231412] hover:text-white transition-all"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									disabled={savingQuickProduct}
									className="px-4 py-1.5 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-bold hover:bg-[#a51f17] transition-all shadow-[2px_2px_0px_#231412]"
								>
									{savingQuickProduct?'Saving...':'Save Material'}
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}

			{mounted&&showPaymentModal&&activePurchase&&createPortal(
				<div className="fixed inset-0 z-[100] bg-[#231412]/50 backdrop-blur-sm flex items-center justify-center p-4">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div>
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">Record Supplier Payment</h3>
								<p className="text-xs text-[#5C403B]">
									PO #{activePurchase.purchase_order_number||activePurchase.id.slice(0,8)} | Outstanding:{' '}
									{formatCurrency(activePurchase.outstanding_amount)}
								</p>
							</div>
							<button
								type="button"
								onClick={()=>setShowPaymentModal(false)}
								className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleRecordPayment} className="space-y-3 font-mono text-xs">
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Amount to Settle (₹)</label>
								<input
									type="number"
									step="0.01"
									required
									value={paymentAmount}
									onChange={(e)=>setPaymentAmount(e.target.value)}
									className="w-full h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Payment Method</label>
								<select
									value={paymentMethod}
									onChange={(e)=>setPaymentMethod(e.target.value)}
									className="w-full h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								>
									<option value="BANK_TRANSFER">Bank Transfer (NEFT / RTGS)</option>
									<option value="UPI">UPI / QR Code</option>
									<option value="CASH">Cash</option>
									<option value="CHEQUE">Cheque</option>
								</select>
							</div>
							<div className="flex items-center justify-end gap-3 pt-4 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setShowPaymentModal(false)}
									className="px-4 py-2 border-2 border-[#231412] bg-[#FAF7F2] text-xs font-bold text-[#231412] hover:bg-[#231412] hover:text-white transition-all"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-5 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-bold hover:bg-[#a51f17] transition-all shadow-[3px_3px_0px_#231412]"
								>
									Post Settlement
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
