'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {useToast} from '@/components/ui';
import React,{useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import {useParams} from 'next/navigation';
import {
	Receipt,
	PlusCircle,
	CheckCircle,
	Clock,
	Ban,
	Trash2,
	CreditCard,
	FileDown,
	Plus,
	X,
	Boxes,
	Edit2,
} from 'lucide-react';
import {
	businessApi,
	SalesInvoice,
	Customer,
	Product,
	SalesInvoiceItem,
	downloadAuthenticatedReport,
} from '../../../../lib/business-api';
import {addMoney,applyDiscountAndTax,formatINR,mulMoneyQty,toMinorUnits} from '../../../../lib/money';

function safeMoney(operation:()=>string):string{
	try{return operation();}catch{return '0.00';}
}

function lineSubtotal(item:SalesInvoiceItem):string{
	return safeMoney(()=>mulMoneyQty(item.unit_price,item.quantity));
}

function lineTax(item:SalesInvoiceItem):string{
	return safeMoney(()=>applyDiscountAndTax(
		lineSubtotal(item),'0',item.tax_rate_pct??'0',
	).tax);
}

const STANDARD_COMMERCIAL_ITEMS=[
	{id:'std-consulting',name:'Engineering & Technical Consulting',unit_price:'2500',tax_rate_pct:'18'},
	{id:'std-assembly',name:'Fabrication & Assembly Deliverable',unit_price:'12000',tax_rate_pct:'18'},
	{id:'std-hardware',name:'Standard Hardware Component Unit',unit_price:'1500',tax_rate_pct:'18'},
	{id:'std-maintenance',name:'Maintenance & Calibration Contract',unit_price:'4500',tax_rate_pct:'18'},
	{id:'std-raw-material',name:'Industrial Raw Material Supply Lot',unit_price:'3200',tax_rate_pct:'12'},
	{id:'std-freight',name:'Logistics, Freight & Delivery',unit_price:'750',tax_rate_pct:'5'},
];

export default function SalesInvoicingPage(){
	const {toast}=useToast();
	const params=useParams();
	const businessId=params.id as string;

	const [invoices,setInvoices]=useState<SalesInvoice[]>([]);
	const [customers,setCustomers]=useState<Customer[]>([]);
	const [products,setProducts]=useState<Product[]>([]);
	const [loading,setLoading]=useState(true);

	const [showCreateModal,setShowCreateModal]=useState(false);
	const [editingInvoice,setEditingInvoice]=useState<SalesInvoice|null>(null);
	const [selectedCustomerId,setSelectedCustomerId]=useState('');
	const [customerName,setCustomerName]=useState('');
	const [customerPhone,setCustomerPhone]=useState('');
	const [invoiceDate,setInvoiceDate]=useState(new Date().toISOString().split('T')[0]);
	const [dueDate,setDueDate]=useState('');
	const [lineItems,setLineItems]=useState<SalesInvoiceItem[]>([
		{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'},
	]);
	const [isCashSale,setIsCashSale]=useState(false);

	const [showPaymentModal,setShowPaymentModal]=useState(false);
	const [activeInvoice,setActiveInvoice]=useState<SalesInvoice|null>(null);
	const [paymentAmount,setPaymentAmount]=useState('');
	const [paymentMethod,setPaymentMethod]=useState('BANK_TRANSFER');

	const [showQuickAddModal,setShowQuickAddModal]=useState(false);
	const [quickAddTargetIndex,setQuickAddTargetIndex]=useState<number|null>(null);
	const [quickProdName,setQuickProdName]=useState('');
	const [quickProdSku,setQuickProdSku]=useState('');
	const [quickProdCategory,setQuickProdCategory]=useState('FINISHED_GOODS');
	const [quickProdPrice,setQuickProdPrice]=useState('1000');
	const [quickProdCost,setQuickProdCost]=useState('600');
	const [quickProdStock,setQuickProdStock]=useState('20');
	const [savingQuickProduct,setSavingQuickProduct]=useState(false);
	const [mounted,setMounted]=useState(false);

	useEffect(()=>{
		setMounted(true);
	},[]);

	useEffect(()=>{
		async function loadData(){
			try{
				const [invList,custList,prodList]=await Promise.all([
					businessApi.listInvoices(businessId).catch(()=>[]),
					businessApi.listCustomers(businessId).catch(()=>[]),
					businessApi.listProducts(businessId).catch(()=>[]),
				]);
				setInvoices(invList);
				setCustomers(custList);
				setProducts(prodList);
			}catch(err){
				console.error('Failed to load invoicing data',err);
			}finally{
				setLoading(false);
			}
		}
		loadData();
	},[businessId]);

	const handleDescriptionChange=(index:number,text:string)=>{
		const updated=[...lineItems];
		const matchedProduct=products.find((p)=>p.name.toLowerCase()===text.trim().toLowerCase());
		const matchedStd=STANDARD_COMMERCIAL_ITEMS.find((s)=>s.name.toLowerCase()===text.trim().toLowerCase());
		if(matchedProduct){
			updated[index]={
				...updated[index],
				item_description:text,
				product_id:matchedProduct.id,
				unit_price:updated[index].unit_price==='0'||!updated[index].unit_price?String(matchedProduct.selling_price_amount):updated[index].unit_price,
			};
		}else if(matchedStd){
			updated[index]={
				...updated[index],
				item_description:text,
				product_id:null,
				unit_price:updated[index].unit_price==='0'||!updated[index].unit_price?matchedStd.unit_price:updated[index].unit_price,
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

	const updateLineItem=(index:number,field:keyof SalesInvoiceItem,val:any)=>{
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

	const handleCustomerNameChange=(name:string)=>{
		setCustomerName(name);
		const match=customers.find((c)=>c.name.trim().toLowerCase()===name.trim().toLowerCase());
		if(match){
			setSelectedCustomerId(match.id);
			if(match.phone)setCustomerPhone(match.phone);
		}else if(name.trim().toLowerCase().includes('walk-in')||name.trim().toLowerCase().includes('cash')){
			setSelectedCustomerId('');
		}
	};

	const handleStartCreate=()=>{
		setEditingInvoice(null);
		setSelectedCustomerId('');
		setCustomerName('');
		setCustomerPhone('');
		setIsCashSale(false);
		setInvoiceDate(new Date().toISOString().split('T')[0]);
		setDueDate('');
		setLineItems([{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'}]);
		setShowCreateModal(true);
	};

	const handleStartEdit=(inv:SalesInvoice)=>{
		setEditingInvoice(inv);
		setSelectedCustomerId(inv.customer_id||'');
		const existingCust=customers.find((c)=>c.id===inv.customer_id);
		let phone='';
		let name=existingCust?existingCust.name:'';
		if(existingCust&&existingCust.phone)phone=existingCust.phone;
		if(!name&&inv.notes){
			const matchName=inv.notes.match(/Customer:\s*([^|;\n]+)/i);
			if(matchName)name=matchName[1].trim();
			const matchPhone=inv.notes.match(/Phone:\s*([^|;\n]+)/i);
			if(matchPhone)phone=matchPhone[1].trim();
		}
		if(!name&&!inv.customer_id)name='Walk-in / Cash Customer';
		setCustomerName(name);
		setCustomerPhone(phone);
		setInvoiceDate(inv.invoice_date);
		setDueDate(inv.due_date||'');
		setLineItems(
			inv.items&&inv.items.length>0
				?inv.items.map((it)=>({
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

	const handleSaveInvoice=async(e:React.FormEvent)=>{
		e.preventDefault();
		try{
			let custId=selectedCustomerId||null;
			const trimmedName=customerName.trim();
			const trimmedPhone=customerPhone.trim();
			if(trimmedName&&!trimmedName.toLowerCase().includes('walk-in')&&!trimmedName.toLowerCase().includes('cash')){
				const match=customers.find((c)=>c.name.trim().toLowerCase()===trimmedName.toLowerCase());
				if(match){
					custId=match.id;
					if(trimmedPhone&&match.phone!==trimmedPhone){
						try{
							await businessApi.updateCustomer(businessId,match.id,{phone:trimmedPhone});
						}catch{}
					}
				}else{
					try{
						const createdCust=await businessApi.createCustomer(businessId,{
							name:trimmedName,
							phone:trimmedPhone,
						});
						custId=createdCust.id;
						setCustomers((prev)=>[...prev,createdCust]);
					}catch{}
				}
			}
			const notesStr=`Customer: ${trimmedName||'Walk-in / Cash Customer'}${trimmedPhone?` | Phone: ${trimmedPhone}`:''}`;
			const processedItems=[...lineItems];
			for(let i=0;i<processedItems.length;i++){
				const item=processedItems[i];
				const desc=item.item_description.trim();
				if(!item.product_id&&desc){
					const matchProd=products.find((p)=>p.name.trim().toLowerCase()===desc.toLowerCase());
					if(matchProd){
						processedItems[i]={...item,product_id:matchProd.id};
					}
				}
			}
			if(editingInvoice){
				const updated=await businessApi.updateInvoice(businessId,editingInvoice.id,{
					customer_id:custId,
					invoice_number:editingInvoice.invoice_number,
					invoice_date:invoiceDate,
					due_date:dueDate||null,
					items:processedItems,
					tax_amount:calculateTax(),
					notes:notesStr,
				});
				setInvoices(invoices.map((i)=>(i.id===updated.id?updated:i)));
				setShowCreateModal(false);
				setEditingInvoice(null);
				toast.success(`Sales invoice ${updated.invoice_number} successfully updated!`);
				if(typeof window!=='undefined'){
					window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
				}
			}else{
				const created=await businessApi.createInvoice(businessId,{
					customer_id:custId,
					invoice_date:invoiceDate,
					due_date:dueDate||null,
					items:processedItems,
					tax_amount:calculateTax(),
					notes:notesStr,
					is_cash_sale:isCashSale,
					immediate_payment_method:isCashSale?'CASH':undefined,
				});
				setInvoices([created,...invoices]);
				setShowCreateModal(false);
				setLineItems([{item_description:'',quantity:'1',unit_price:'0',tax_rate_pct:'18'}]);
				toast.success(`Sales invoice ${created.invoice_number} successfully issued!`);
				if(typeof window!=='undefined'){
					window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
				}
			}
		}catch(err:any){
			toast.error(`Invoice processing failed: ${err.message}`);
		}
	};

	const handleDeleteInvoice=async(invoiceId:string,invoiceNumber:string)=>{
		if(!window.confirm(`Are you sure you want to delete sales invoice #${invoiceNumber}? This will permanently remove the record and restore inventory.`))return;
		try{
			await businessApi.deleteInvoice(businessId,invoiceId);
			setInvoices(invoices.filter((i)=>i.id!==invoiceId));
			toast.success(`Sales invoice #${invoiceNumber} successfully deleted.`);
			if(typeof window!=='undefined'){
				window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
			}
		}catch(err:any){
			toast.error(`Delete failed: ${err.message}`);
		}
	};

	const handleRecordPayment=async(e:React.FormEvent)=>{
		e.preventDefault();
		if(!activeInvoice)return;
		try{
			const updated=await businessApi.recordInvoicePayment(businessId,activeInvoice.id,{
				amount:paymentAmount,
				payment_method:paymentMethod,
			});
			setInvoices(invoices.map((inv)=>(inv.id===updated.id?updated:inv)));
			setShowPaymentModal(false);
			setActiveInvoice(null);
			setPaymentAmount('');
			toast.success(`Payment of ₹${paymentAmount} collected on invoice ${activeInvoice.invoice_number}!`);
			if(typeof window!=='undefined'){
				window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
			}
		}catch(err:any){
			toast.error(`Payment recording failed: ${err.message}`);
		}
	};

	const handleQuickAddProduct=async(e:React.FormEvent)=>{
		e.preventDefault();
		if(!quickProdName.trim())return;
		setSavingQuickProduct(true);
		try{
			const created=await businessApi.createProduct(businessId,{
				name:quickProdName.trim(),
				sku:quickProdSku.trim()||`SKU-${Date.now().toString().slice(-4)}`,
				category:quickProdCategory,
				unit_of_measure:'pcs',
				selling_price_amount:quickProdPrice,
				purchase_price_amount:quickProdCost,
				current_stock:parseFloat(quickProdStock)||0,
				reorder_level:5,
			});
			const updatedList=await businessApi.listProducts(businessId);
			setProducts(updatedList);
			if(quickAddTargetIndex!==null&&quickAddTargetIndex<lineItems.length){
				const updated=[...lineItems];
				updated[quickAddTargetIndex]={
					...updated[quickAddTargetIndex],
					product_id:created.id,
					item_description:created.name,
					quantity:updated[quickAddTargetIndex].quantity||'1',
					unit_price:String(created.selling_price_amount),
					tax_rate_pct:created.tax_rate_pct||'18',
				};
				setLineItems(updated);
			}
			setShowQuickAddModal(false);
			setQuickProdName('');
			setQuickProdSku('');
			toast.success(`Product "${created.name}" established in inventory.`);
		}catch(err:any){
			toast.error(`Product registration failed: ${err.message}`);
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
			<datalist id="products-catalog-suggestions">
				{products.map((p)=>(
					<option key={p.id} value={p.name}>{`₹${p.selling_price_amount} | Available: ${p.current_stock} units`}</option>
				))}
				{STANDARD_COMMERCIAL_ITEMS.map((s)=>(
					<option key={s.id} value={s.name}>{`₹${s.unit_price} | Standard Service`}</option>
				))}
			</datalist>

			<div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b-2 border-[#231412]">
				<div>
					<h1 className="text-2xl font-black text-[#231412] uppercase tracking-wide">Sales & Invoicing</h1>
					<p className="text-xs font-mono text-[#5C403B] mt-0.5">
						Automated inventory deduction, double-entry revenue journals, and collection tracking.
					</p>
				</div>

				<MotionButton
					onClick={handleStartCreate}
					className="px-4 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-mono font-bold shadow-[3px_3px_0px_#231412] hover:bg-[#a51f17] transition-all flex items-center gap-1.5"
				>
					<Plus size={16} />
					<span>New Sales Invoice</span>
				</MotionButton>
			</div>

			<div className="p-6 bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412]">
				{invoices.length===0?(
					<div className="text-center py-12 text-xs font-mono text-[#5C403B]">
						No sales invoices created yet. Click &ldquo;New Sales Invoice&rdquo; to issue an invoice.
					</div>
				):(
					<div className="overflow-x-auto">
						<table className="w-full text-left text-xs font-mono">
							<thead>
								<tr className="border-b-2 border-[#231412] text-[#231412] uppercase font-bold text-[11px]">
									<th className="py-3 px-4">Invoice #</th>
									<th className="py-3 px-4">Date</th>
									<th className="py-3 px-4">Due Date</th>
									<th className="py-3 px-4 text-right">Total Amount</th>
									<th className="py-3 px-4 text-right">Outstanding</th>
									<th className="py-3 px-4 text-center">Status</th>
									<th className="py-3 px-4 text-center">Actions</th>
								</tr>
							</thead>
							<tbody className="divide-y border-b border-[#231412]/15">
								{invoices.map((inv)=>(
									<tr key={inv.id} className="hover:bg-[#FAF7F2]">
										<td className="py-3 px-4 font-bold text-[#231412]">{inv.invoice_number}</td>
										<td className="py-3 px-4 text-[#5C403B]">{inv.invoice_date}</td>
										<td className="py-3 px-4 text-[#5C403B]">{inv.due_date||'—'}</td>
										<td className="py-3 px-4 text-right font-bold text-[#231412]">
											{formatCurrency(inv.total_amount)}
										</td>
										<td className="py-3 px-4 text-right font-bold text-[#10B981]">
											{formatCurrency(inv.outstanding_amount)}
										</td>
										<td className="py-3 px-4 text-center">
											<span
												className={`px-2 py-0.5 border text-[10px] font-bold ${
													inv.status==='PAID'
														?'bg-[#10B981]/15 text-[#10B981] border-[#10B981]'
														:inv.status==='PARTIALLY_PAID'
														?'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]'
														:inv.status==='CANCELLED'
														?'bg-[#231412]/10 text-[#5C403B] border-[#231412]/30'
														:'bg-[#C8281E]/15 text-[#C8281E] border-[#C8281E]'
												}`}
											>
												{inv.status}
											</span>
										</td>
										<td className="py-3 px-4 text-center">
											<div className="flex items-center justify-center gap-1.5">
												{toMinorUnits(inv.outstanding_amount)>BigInt(0)&&inv.status!=='CANCELLED'&&(
													<MotionButton
														onClick={()=>{
															setActiveInvoice(inv);
															setPaymentAmount(String(inv.outstanding_amount));
															setShowPaymentModal(true);
														}}
														className="px-2 py-1 border border-[#231412] bg-[#FAF7F2] text-[#231412] hover:bg-[#C8281E] hover:text-white text-[10px] font-mono font-bold transition-all shadow-[1px_1px_0px_#231412]"
													>
														Collect Payment
													</MotionButton>
												)}
												{inv.status!=='CANCELLED'&&(
													<MotionButton
														type="button"
														onClick={()=>handleStartEdit(inv)}
														title="Edit Sales Invoice"
														className="p-1 border border-[#231412]/30 text-[#231412] hover:bg-[#FAF7F2] hover:border-[#231412] hover:text-[#C8281E] transition-colors inline-flex items-center"
													>
														<Edit2 className="w-3.5 h-3.5" />
													</MotionButton>
												)}
												<MotionButton
													type="button"
													onClick={()=>handleDeleteInvoice(inv.id,inv.invoice_number)}
													title="Delete Sales Invoice"
													className="p-1 border border-[#231412]/30 text-[#231412] hover:bg-[#C8281E] hover:text-white hover:border-[#C8281E] transition-colors inline-flex items-center"
												>
													<Trash2 className="w-3.5 h-3.5" />
												</MotionButton>
												<MotionButton
													type="button"
													onClick={()=>downloadAuthenticatedReport(
														businessApi.getTaxInvoicePdfUrl(businessId,inv.id),
														`invoice-${inv.invoice_number}.pdf`,
													).catch((err:Error)=>toast.error(`Invoice download failed: ${err.message}`))}
													title="Download Camera-Ready Tax Invoice PDF"
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
									{editingInvoice?`Edit Sales Invoice #${editingInvoice.invoice_number}`:'Issue Sales Invoice'}
								</h3>
								<p className="text-xs text-[#5C403B]">Automated inventory deduction, double-entry revenue journal, and collection ledger.</p>
							</div>
							<button
								type="button"
								onClick={()=>setShowCreateModal(false)}
								className="p-1.5 border-2 border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleSaveInvoice} className="flex flex-col flex-1 min-h-0">
							<div className="overflow-y-auto flex-1 pr-1 space-y-4">
								<div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 bg-white border-2 border-[#231412]/20">
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
											Customer Name (Write directly)
										</label>
										<input
											type="text"
											list="customers-catalog-suggestions"
											placeholder="Write customer or company name..."
											value={customerName}
											onChange={(e)=>handleCustomerNameChange(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
										<datalist id="customers-catalog-suggestions">
											<option value="Walk-in / Cash Customer" />
											{customers.map((c)=>(
												<option key={c.id} value={c.name}>
													{c.phone?`${c.name} (${c.phone})`:c.name}
												</option>
											))}
										</datalist>
									</div>
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
											Customer Mobile / Phone
										</label>
										<input
											type="tel"
											placeholder="+91 98765 43210"
											value={customerPhone}
											onChange={(e)=>setCustomerPhone(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">Invoice Date</label>
										<input
											type="date"
											required
											value={invoiceDate}
											onChange={(e)=>setInvoiceDate(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
									<div className="md:col-span-2">
										<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">Due Date</label>
										<input
											type="date"
											value={dueDate}
											onChange={(e)=>setDueDate(e.target.value)}
											className="w-full text-xs h-9 px-2.5 bg-[#FAF7F2] border-2 border-[#231412] font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
								</div>

								{!editingInvoice&&(
									<div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-white border-2 border-[#231412]/20">
										<div>
											<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase tracking-wider mb-1">
												Settlement Terms
											</label>
											<div className="flex border-2 border-[#231412]">
												<button
													type="button"
													onClick={()=>setIsCashSale(false)}
													className={`flex-1 py-1.5 text-xs font-mono font-bold uppercase transition-all ${!isCashSale?'bg-[#231412] text-white':'bg-[#FAF7F2] text-[#231412]'}`}
												>
													Credit (Receivable)
												</button>
												<div className="w-0.5 bg-[#231412]" />
												<button
													type="button"
													onClick={()=>setIsCashSale(true)}
													className={`flex-1 py-1.5 text-xs font-mono font-bold uppercase transition-all ${isCashSale?'bg-emerald-700 text-white':'bg-[#FAF7F2] text-[#231412]'}`}
												>
													Cash (Immediate Inflow)
												</button>
											</div>
										</div>
										<div className="flex flex-col justify-center">
											<span className="text-[10px] font-mono text-[#5C403B]">
												{isCashSale?'Immediate Cash Sale: deposits cash directly into Liquid Cash.':'Credit Sale: records invoice into Accounts Receivable until payment is collected.'}
											</span>
										</div>
									</div>
								)}

								<div className="border-2 border-[#231412]/20 p-3 bg-white space-y-3">
									<div className="flex items-center justify-between pb-1 border-b border-[#231412]/15">
										<span className="text-xs font-mono font-bold text-[#231412] uppercase tracking-wider">
											Line Items ({lineItems.length})
										</span>
										<button
											type="button"
											onClick={()=>{
												setQuickAddTargetIndex(lineItems.length-1);
												setShowQuickAddModal(true);
											}}
											className="text-[11px] font-mono text-[#C8281E] hover:underline font-bold"
										>
											+ Quick Add Product to Inventory
										</button>
									</div>

									<div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
										{lineItems.map((item,idx)=>(
											<div key={idx} className="grid grid-cols-12 gap-2 items-end p-2.5 bg-[#FAF7F2] border-2 border-[#231412]/15">
												<div className="col-span-5">
													<label className="block text-[10px] font-mono font-bold text-[#231412] uppercase mb-1">
														Item Name / Description (Write directly)
													</label>
													<input
														type="text"
														required
														list="products-catalog-suggestions"
														value={item.item_description}
														onChange={(e)=>handleDescriptionChange(idx,e.target.value)}
														placeholder="Write item name, service, or part..."
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
														Price (₹)
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
														<option value="12">12% (Machinery)</option>
														<option value="5">5% (Logistics / Basic)</option>
														<option value="0">0% (Exempt / Nil)</option>
														<option value="28">28% (Luxury Slab)</option>
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
										<span>Central Tax (CGST @ 9%):</span>
										<span>{formatCurrency(Number(calculateTax())/2)}</span>
									</div>
									<div className="flex justify-between text-[#5C403B]">
										<span>State Tax (SGST @ 9%):</span>
										<span>{formatCurrency(Number(calculateTax())/2)}</span>
									</div>
									<div className="flex justify-between text-[#5C403B] font-bold">
										<span>Total Tax (GST):</span>
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
									{editingInvoice?'Update Invoice':'Issue Invoice'}
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}

			{mounted&&showQuickAddModal&&createPortal(
				<div className="fixed inset-0 z-[110] bg-[#231412]/60 backdrop-blur-sm overflow-y-auto p-4 flex justify-center items-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div className="flex items-center gap-2">
								<Boxes size={18} className="text-[#C8281E]" />
								<h3 className="text-sm font-black text-[#231412] uppercase tracking-wide">Register New Inventory Product</h3>
							</div>
							<button
								type="button"
								onClick={()=>setShowQuickAddModal(false)}
								className="p-1 border border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white"
							>
								<X size={14} />
							</button>
						</div>

						<form onSubmit={handleQuickAddProduct} className="space-y-3 font-mono">
							<div>
								<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Product Name *</label>
								<input
									type="text"
									required
									value={quickProdName}
									onChange={(e)=>setQuickProdName(e.target.value)}
									placeholder="e.g. High Torque Electric Motor"
									className="w-full text-xs h-9 px-2.5 bg-white border-2 border-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">SKU Code</label>
									<input
										type="text"
										value={quickProdSku}
										onChange={(e)=>setQuickProdSku(e.target.value)}
										placeholder="e.g. MTR-EL-10"
										className="w-full text-xs h-9 px-2.5 bg-white border-2 border-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Category</label>
									<select
										value={quickProdCategory}
										onChange={(e)=>setQuickProdCategory(e.target.value)}
										className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] focus:outline-none focus:border-[#C8281E]"
									>
										<option value="FINISHED_GOODS">Finished Goods</option>
										<option value="RAW_MATERIALS">Raw Materials</option>
										<option value="CONSUMABLES">Consumables</option>
										<option value="SERVICES">Services</option>
									</select>
								</div>
							</div>
							<div className="grid grid-cols-3 gap-3">
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Selling (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={quickProdPrice}
										onChange={(e)=>setQuickProdPrice(e.target.value)}
										className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Cost (₹)</label>
									<input
										type="number"
										step="0.01"
										required
										value={quickProdCost}
										onChange={(e)=>setQuickProdCost(e.target.value)}
										className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
								<div>
									<label className="block text-[10px] font-bold text-[#231412] uppercase mb-1">Opening Qty</label>
									<input
										type="number"
										step="any"
										required
										value={quickProdStock}
										onChange={(e)=>setQuickProdStock(e.target.value)}
										className="w-full text-xs h-9 px-2 bg-white border-2 border-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
							</div>

							<div className="flex items-center justify-end gap-3 pt-4 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setShowQuickAddModal(false)}
									className="px-3.5 py-1.5 border-2 border-[#231412] bg-[#FAF7F2] text-xs font-bold text-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									disabled={savingQuickProduct}
									className="px-4 py-1.5 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-bold shadow-[2px_2px_0px_#231412]"
								>
									{savingQuickProduct?'Saving...':'Save Product'}
								</MotionButton>
							</div>
						</form>
					</div>
				</div>,
				document.body
			)}

			{mounted&&showPaymentModal&&activeInvoice&&createPortal(
				<div className="fixed inset-0 z-[100] bg-[#231412]/50 backdrop-blur-sm overflow-y-auto p-4 flex justify-center items-center">
					<div className="bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] max-w-md w-full p-6 animate-in zoom-in-95">
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-4">
							<div>
								<h3 className="text-base font-black text-[#231412] uppercase tracking-wide">Record Invoice Payment</h3>
								<p className="text-xs font-mono text-[#5C403B]">
									Invoice #{activeInvoice.invoice_number} | Outstanding: {formatCurrency(activeInvoice.outstanding_amount)}
								</p>
							</div>
							<button
								type="button"
								onClick={()=>setShowPaymentModal(false)}
								className="p-1 border border-[#231412] text-[#231412] bg-white hover:bg-[#C8281E] hover:text-white"
							>
								<X size={16} />
							</button>
						</div>

						<form onSubmit={handleRecordPayment} className="space-y-4 font-mono">
							<div>
								<label className="block text-xs font-bold text-[#231412] uppercase mb-1">Amount to Collect (₹)</label>
								<input
									type="number"
									step="0.01"
									required
									value={paymentAmount}
									onChange={(e)=>setPaymentAmount(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-bold text-[#231412] uppercase mb-1">Payment Channel</label>
								<select
									value={paymentMethod}
									onChange={(e)=>setPaymentMethod(e.target.value)}
									className="w-full text-xs h-9 px-3 bg-white border-2 border-[#231412] text-[#231412] focus:outline-none focus:border-[#C8281E]"
								>
									<option value="BANK_TRANSFER">Bank Transfer (NEFT/RTGS/IMPS)</option>
									<option value="UPI">UPI / QR Code</option>
									<option value="CASH">Cash in Hand</option>
									<option value="CHEQUE">Cheque</option>
								</select>
							</div>
							<div className="flex items-center justify-end gap-3 pt-3 border-t-2 border-[#231412]">
								<MotionButton
									type="button"
									onClick={()=>setShowPaymentModal(false)}
									className="px-3.5 py-1.5 border-2 border-[#231412] bg-[#FAF7F2] text-xs font-bold text-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 border-2 border-[#231412] bg-[#C8281E] text-white text-xs font-bold shadow-[3px_3px_0px_#231412] hover:bg-[#a51f17]"
								>
									Apply Payment
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
