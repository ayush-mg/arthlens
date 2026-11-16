'use client';
	const workspaceRoutes = [
		{ path: '', label: 'Overview', code: 'OV' },
		{ path: 'sales', label: 'Sales', code: 'SL' },
		{ path: 'purchases', label: 'Purchases', code: 'PU' },
		{ path: 'inventory', label: 'Inventory', code: 'IN' },
		{ path: 'khata', label: 'Khata', code: 'KH' },
		{ path: 'finance', label: 'Finance', code: 'FI' },
		{ path: 'decisions', label: 'Decisions', code: 'DE' },
		{ path: 'scenarios', label: 'Scenarios', code: 'SC' },
		{ path: 'goals', label: 'Goals', code: 'GO' },
		{ path: 'analytics', label: 'Analytics', code: 'AN' },
		{ path: 'agent', label: 'AI Agent', code: 'AI' },
		{ path: 'customers', label: 'Customers', code: 'CU' },
		{ path: 'suppliers', label: 'Suppliers', code: 'SU' },
		{ path: 'reports', label: 'Reports', code: 'RE' },
		{ path: 'audit', label: 'Audit & Access', code: 'AU' },
		{ path: 'members', label: 'Members', code: 'ME' },
		{ path: 'settings', label: 'Settings', code: 'ST' },
		{ path: 'constellation', label: 'Constellation', code: 'CN' },
	];
	const workspaceDescriptions = [
		'Executive pulse and KPIs', 'Invoices, POS and revenue', 'Bills and procurement', 'Units, SKUs and inventory',
		'Ledger and credit book', 'Cash flow, P&L and runway', 'Strategic action engine', 'What-if simulations',
		'Targets and milestones', 'Business intelligence', 'Decision co-pilot', 'Client accounts and CRM',
		'Vendor network and payables', 'GST, tax and statements', 'Immutable activity trail', 'Team roles and access',
		'Workspace configuration', 'Business entity graph',
	];
	export function getWorkspaceDecks(workspaceId: string) {
		return workspaceRoutes.map((route, index) => ({
			...route,
			subtitle: workspaceDescriptions[index],
			href: `/workspaces/${workspaceId}${route.path ? `/${route.path}` : ''}`,
		}));
	}
	export function WorkspaceModuleRail() {
		return null;
	}
	export default WorkspaceModuleRail;
