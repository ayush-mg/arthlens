'use client';
import { MotionButton } from '@/components/ui/motion-button';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  BrainCircuit,
  Play,
  Dices,
  BarChart3,
  FileDown,
  Award,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Sparkles,
  History,
  TrendingUp,
  Calculator,
} from 'lucide-react';
import {
  businessApi,
  DecisionEvaluationResult,
  DecisionVersion,
  MonteCarloRiskResult,
  SensitivityAnalysisResult,
  downloadAuthenticatedReport,
} from '../../../../lib/business-api';
import { useToast } from '@/components/ui';

export default function DecisionLaboratoryPage() {
  const { toast } = useToast();
  const params = useParams();
  const businessId = params.id as string;

  const [selectedModel, setSelectedModel] = useState<string>('MACHINE_OR_EQUIPMENT_PURCHASE');
  const [decisionTitle, setDecisionTitle] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [evaluation, setEvaluation] = useState<DecisionEvaluationResult | null>(null);
  const [advancedForm, setAdvancedForm] = useState<Record<string, string>>({});
  const [locationCandidates, setLocationCandidates] = useState<Array<Record<string, string>>>([
    {
      location_name: 'Downtown Commercial Hub',
      fitout_capex: '500000',
      monthly_rent: '45000',
      monthly_staff_cost: '35000',
      catchment_monthly_demand: '1500',
      conversion_rate_pct: '5.5',
      average_order_value: '750',
      gross_margin_pct: '45',
      cannibalization_pct: '5',
    },
    {
      location_name: 'Suburban Retail High-Street',
      fitout_capex: '350000',
      monthly_rent: '30000',
      monthly_staff_cost: '25000',
      catchment_monthly_demand: '1100',
      conversion_rate_pct: '4.8',
      average_order_value: '680',
      gross_margin_pct: '42',
      cannibalization_pct: '2',
    },
  ]);

  // Monte Carlo simulation state
  const [simulating, setSimulating] = useState(false);
  const [monteCarlo, setMonteCarlo] = useState<MonteCarloRiskResult | null>(null);

  // Sensitivity state
  const [sensitivityLoading, setSensitivityLoading] = useState(false);
  const [sensitivity, setSensitivity] = useState<SensitivityAnalysisResult | null>(null);

  // Past evaluations history
  const [history, setHistory] = useState<any[]>([]);
  const [versionHistory, setVersionHistory] = useState<DecisionVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);

  useEffect(() => {
    if (!businessId) return;
    businessApi.getDecisionHistory(businessId)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [businessId]);

  // ---------------------------------------------------------------------------
  // Model 1: Machine / Equipment Purchase
  // ---------------------------------------------------------------------------
  const [machineName, setMachineName] = useState('');
  const [machineCost, setMachineCost] = useState('');
  const [machineDownPayment, setMachineDownPayment] = useState('');
  const [loanInterestRate, setLoanInterestRate] = useState('');
  const [loanTenureMonths, setLoanTenureMonths] = useState('');
  const [monthlyMaintenance, setMonthlyMaintenance] = useState('');
  const [currentMonthlyVolume, setCurrentMonthlyVolume] = useState('');
  const [capacityMonthlyVolume, setCapacityMonthlyVolume] = useState('');
  const [equipmentUnitPrice, setEquipmentUnitPrice] = useState('');
  const [equipmentVariableCost, setEquipmentVariableCost] = useState('');

  // ---------------------------------------------------------------------------
  // Model 2: New Product Addition
  // ---------------------------------------------------------------------------
  const [productName, setProductName] = useState('');
  const [productSellingPrice, setProductSellingPrice] = useState('');
  const [productVariableCost, setProductVariableCost] = useState('');
  const [productMonthlyVolume, setProductMonthlyVolume] = useState('');
  const [productSetupCost, setProductSetupCost] = useState('');
  const [productCannibalizationRate, setProductCannibalizationRate] = useState('');

  // ---------------------------------------------------------------------------
  // Model 3: Supplier Switch or Credit Terms
  // ---------------------------------------------------------------------------
  const [supplierName, setSupplierName] = useState('');
  const [supplierCurrentPrice, setSupplierCurrentPrice] = useState('');
  const [supplierNewPrice, setSupplierNewPrice] = useState('');
  const [supplierMonthlyUnits, setSupplierMonthlyUnits] = useState('');
  const [supplierCurrentCreditDays, setSupplierCurrentCreditDays] = useState('');
  const [supplierNewCreditDays, setSupplierNewCreditDays] = useState('');
  const [supplierSwitchingCost, setSupplierSwitchingCost] = useState('');

  // ---------------------------------------------------------------------------
  // Model 4: Bulk Discount vs Storage Cost
  // ---------------------------------------------------------------------------
  const [bulkRegularPrice, setBulkRegularPrice] = useState('');
  const [bulkDiscountedPrice, setBulkDiscountedPrice] = useState('');
  const [bulkOrderQty, setBulkOrderQty] = useState('');
  const [bulkMonthlyConsumption, setBulkMonthlyConsumption] = useState('');
  const [bulkStorageCostPerUnit, setBulkStorageCostPerUnit] = useState('');
  const [bulkCostOfCapital, setBulkCostOfCapital] = useState('');

  // ---------------------------------------------------------------------------
  // Model 5: New Branch / Location Opening
  // ---------------------------------------------------------------------------
  const [branchLocationName, setBranchLocationName] = useState('');
  const [branchFitoutCapex, setBranchFitoutCapex] = useState('');
  const [branchSecurityDeposit, setBranchSecurityDeposit] = useState('');
  const [branchMonthlyRent, setBranchMonthlyRent] = useState('');
  const [branchMonthlyStaffCost, setBranchMonthlyStaffCost] = useState('');
  const [branchMonthlyUtilities, setBranchMonthlyUtilities] = useState('');
  const [branchDailyCustomers, setBranchDailyCustomers] = useState('');
  const [branchAvgOrderValue, setBranchAvgOrderValue] = useState('');
  const [branchGrossMarginPct, setBranchGrossMarginPct] = useState('');

  // ---------------------------------------------------------------------------
  // Model 6: Hiring Staff or Commission Structure
  // ---------------------------------------------------------------------------
  const [staffRoleTitle, setStaffRoleTitle] = useState('');
  const [staffMonthlySalary, setStaffMonthlySalary] = useState('');
  const [staffCommissionPct, setStaffCommissionPct] = useState('');
  const [staffBenefitsOverhead, setStaffBenefitsOverhead] = useState('');
  const [staffExpectedRevenue, setStaffExpectedRevenue] = useState('');
  const [staffGrossMarginPct, setStaffGrossMarginPct] = useState('');

  // ---------------------------------------------------------------------------
  // Model 7: Credit Term Extension to Customer
  // ---------------------------------------------------------------------------
  const [creditCustomerName, setCreditCustomerName] = useState('');
  const [creditCurrentMonthlySales, setCreditCurrentMonthlySales] = useState('');
  const [creditExpectedGrowthPct, setCreditExpectedGrowthPct] = useState('');
  const [creditCurrentTermsDays, setCreditCurrentTermsDays] = useState('');
  const [creditProposedTermsDays, setCreditProposedTermsDays] = useState('');
  const [creditGrossMarginPct, setCreditGrossMarginPct] = useState('');
  const [creditDefaultRiskPct, setCreditDefaultRiskPct] = useState('');
  const [creditCostOfCapitalPct, setCreditCostOfCapitalPct] = useState('');

  // ---------------------------------------------------------------------------
  // Model 8: Price Increase vs Demand Elasticity
  // ---------------------------------------------------------------------------
  const [priceProductName, setPriceProductName] = useState('');
  const [priceCurrentPrice, setPriceCurrentPrice] = useState('');
  const [priceProposedPrice, setPriceProposedPrice] = useState('');
  const [priceCurrentVolume, setPriceCurrentVolume] = useState('');
  const [priceUnitVariableCost, setPriceUnitVariableCost] = useState('');
  const [priceElasticity, setPriceElasticity] = useState('');

  const modelsList = [
    { key: 'MACHINE_OR_EQUIPMENT_PURCHASE', label: 'Machine / Equipment Purchase' },
    { key: 'NEW_PRODUCT_ADDITION', label: 'New Product Line Addition' },
    { key: 'SUPPLIER_SWITCH_OR_CREDIT_TERMS', label: 'Supplier Switch or Credit Terms' },
    { key: 'BULK_DISCOUNT_VS_STORAGE_COST', label: 'Bulk Discount vs Storage Cost' },
    { key: 'NEW_BRANCH_OR_LOCATION_OPENING', label: 'New Branch / Location Opening' },
    { key: 'HIRING_STAFF_OR_COMMISSION', label: 'Hiring Staff or Commission Structure' },
    { key: 'CREDIT_TERM_EXTENSION_TO_CUSTOMER', label: 'Credit Term Extension to Customer' },
    { key: 'PRICE_INCREASE_OR_DISCOUNT', label: 'Price Increase vs Demand Elasticity' },
    { key: 'FINANCING_COMPARISON', label: 'Loan vs Lease vs Equity Financing' },
    { key: 'BUSINESS_EXPANSION', label: 'Business Expansion Funding' },
    { key: 'INVENTORY_PROCUREMENT', label: 'Inventory Procurement' },
    { key: 'CUSTOMER_CREDIT_RISK', label: 'Customer Credit Risk' },
    { key: 'COST_REDUCTION', label: 'Cost Reduction' },
    { key: 'CASH_FLOW_PRESSURE', label: 'Cash-Flow Pressure' },
    { key: 'BUSINESS_VIABILITY', label: 'Business Viability & Solvency' },
    { key: 'LOCATION_SELECTION', label: 'Location Selection' },
  ];

  interface FieldSpec {
    key: string;
    label: string;
    unit?: string;
    placeholder?: string;
    type?: 'text' | 'number';
  }

  const advancedModelSpecs: Record<string, FieldSpec[]> = {
    FINANCING_COMPARISON: [
      { key: 'purchase_cost', label: 'Purchase Cost / Total Capex', unit: '₹', placeholder: '100000', type: 'number' },
      { key: 'monthly_operating_gain', label: 'Monthly Operating Gain', unit: '₹', placeholder: '15000', type: 'number' },
      { key: 'available_cash', label: 'Available Cash in Hand', unit: '₹', placeholder: '50000', type: 'number' },
      { key: 'loan_interest_rate_pct', label: 'Loan Annual Interest Rate', unit: '%', placeholder: '11.5', type: 'number' },
      { key: 'loan_term_months', label: 'Loan Repayment Term', unit: 'Mo', placeholder: '24', type: 'number' },
      { key: 'lease_monthly_payment', label: 'Lease Monthly Payment', unit: '₹', placeholder: '4500', type: 'number' },
      { key: 'lease_term_months', label: 'Lease Duration', unit: 'Mo', placeholder: '24', type: 'number' },
      { key: 'equity_injection', label: 'Equity Capital Injection', unit: '₹', placeholder: '25000', type: 'number' },
      { key: 'discount_rate_pct', label: 'Hurdle / Discount Rate', unit: '%', placeholder: '10.0', type: 'number' },
    ],
    BUSINESS_EXPANSION: [
      { key: 'expansion_capex', label: 'Expansion Capex', unit: '₹', placeholder: '250000', type: 'number' },
      { key: 'projected_monthly_revenue', label: 'Projected Monthly Inflow', unit: '₹', placeholder: '80000', type: 'number' },
      { key: 'gross_margin_pct', label: 'Gross Profit Margin', unit: '%', placeholder: '40', type: 'number' },
      { key: 'projected_monthly_opex', label: 'Projected Monthly Opex', unit: '₹', placeholder: '25000', type: 'number' },
      { key: 'available_cash', label: 'Available Cash Balance', unit: '₹', placeholder: '100000', type: 'number' },
      { key: 'committed_financing', label: 'Committed External Financing', unit: '₹', placeholder: '150000', type: 'number' },
      { key: 'financing_mode', label: 'Financing Mode (DEBT / EQUITY / INTERNAL)', placeholder: 'DEBT', type: 'text' },
    ],
    INVENTORY_PROCUREMENT: [
      { key: 'unit_cost', label: 'Unit Purchase Cost', unit: '₹', placeholder: '120', type: 'number' },
      { key: 'order_quantity', label: 'Order Batch Quantity', unit: 'Units', placeholder: '500', type: 'number' },
      { key: 'monthly_demand', label: 'Monthly Sales Demand', unit: 'Units', placeholder: '300', type: 'number' },
      { key: 'current_stock', label: 'Current Stock on Hand', unit: 'Units', placeholder: '80', type: 'number' },
      { key: 'reorder_threshold', label: 'Reorder Buffer Point', unit: 'Units', placeholder: '100', type: 'number' },
      { key: 'holding_cost_per_unit_month', label: 'Holding Cost / Unit / Month', unit: '₹', placeholder: '4', type: 'number' },
      { key: 'stockout_cost_per_unit', label: 'Stockout Penalty / Unit', unit: '₹', placeholder: '25', type: 'number' },
      { key: 'supplier_lead_time_days', label: 'Supplier Lead Time', unit: 'Days', placeholder: '7', type: 'number' },
    ],
    CUSTOMER_CREDIT_RISK: [
      { key: 'customer_name', label: 'Customer Account Name', placeholder: 'Metro Traders', type: 'text' },
      { key: 'current_receivable', label: 'Current Outstanding Receivable', unit: '₹', placeholder: '25000', type: 'number' },
      { key: 'credit_limit', label: 'Credit Limit Ceiling', unit: '₹', placeholder: '100000', type: 'number' },
      { key: 'requested_sale_amount', label: 'Requested Order Value', unit: '₹', placeholder: '50000', type: 'number' },
      { key: 'average_monthly_sales', label: 'Average Monthly Sales to Customer', unit: '₹', placeholder: '40000', type: 'number' },
      { key: 'gross_margin_pct', label: 'Gross Margin on Order', unit: '%', placeholder: '30', type: 'number' },
      { key: 'default_risk_pct', label: 'Estimated Default Risk', unit: '%', placeholder: '5', type: 'number' },
      { key: 'annual_cost_of_capital_pct', label: 'Cost of Capital', unit: '%', placeholder: '12', type: 'number' },
      { key: 'proposed_terms_days', label: 'Proposed Credit Terms', unit: 'Days', placeholder: '45', type: 'number' },
      { key: 'overdue_days', label: 'Current Days Overdue', unit: 'Days', placeholder: '0', type: 'number' },
    ],
    COST_REDUCTION: [
      { key: 'cost_category', label: 'Cost Category Name', placeholder: 'Electricity & Utilities', type: 'text' },
      { key: 'current_monthly_cost', label: 'Current Monthly Run-Rate Cost', unit: '₹', placeholder: '45000', type: 'number' },
      { key: 'proposed_monthly_cost', label: 'Proposed Target Cost', unit: '₹', placeholder: '32000', type: 'number' },
      { key: 'one_time_implementation_cost', label: 'One-Time Transition Cost', unit: '₹', placeholder: '15000', type: 'number' },
      { key: 'expected_quality_cost_monthly', label: 'Quality / Rework Cost', unit: '₹', placeholder: '1000', type: 'number' },
      { key: 'evaluation_months', label: 'Evaluation Period Horizon', unit: 'Mo', placeholder: '12', type: 'number' },
    ],
    CASH_FLOW_PRESSURE: [
      { key: 'cash_balance', label: 'Current Cash Balance', unit: '₹', placeholder: '50000', type: 'number' },
      { key: 'monthly_cash_inflows', label: 'Projected Monthly Inflows', unit: '₹', placeholder: '120000', type: 'number' },
      { key: 'monthly_cash_outflows', label: 'Committed Monthly Outflows', unit: '₹', placeholder: '140000', type: 'number' },
      { key: 'receivables_due_30d', label: 'Receivables Maturing in 30 Days', unit: '₹', placeholder: '40000', type: 'number' },
      { key: 'receivables_collectible_amount', label: 'Realistic 30d Collections', unit: '₹', placeholder: '30000', type: 'number' },
      { key: 'payables_due_30d', label: 'Payables Due in 30 Days', unit: '₹', placeholder: '60000', type: 'number' },
      { key: 'payables_deferral_amount', label: 'Negotiable Payables Deferrals', unit: '₹', placeholder: '20000', type: 'number' },
      { key: 'credit_line_available', label: 'Available Credit Facilities', unit: '₹', placeholder: '80000', type: 'number' },
      { key: 'credit_line_draw_amount', label: 'Proposed Facility Draw', unit: '₹', placeholder: '25000', type: 'number' },
      { key: 'credit_line_interest_pct', label: 'Facility Interest Rate', unit: '%', placeholder: '12.5', type: 'number' },
      { key: 'monthly_survival_threshold', label: 'Minimum Survival Buffer', unit: '₹', placeholder: '15000', type: 'number' },
    ],
    BUSINESS_VIABILITY: [
      { key: 'current_monthly_revenue', label: 'Current Monthly Revenue', unit: '₹', placeholder: '200000', type: 'number' },
      { key: 'variable_cost_pct', label: 'Variable Cost Ratio', unit: '%', placeholder: '55', type: 'number' },
      { key: 'monthly_fixed_costs', label: 'Monthly Fixed Costs', unit: '₹', placeholder: '60000', type: 'number' },
      { key: 'cash_balance', label: 'Liquid Cash Balance', unit: '₹', placeholder: '120000', type: 'number' },
      { key: 'monthly_debt_service', label: 'Monthly Debt Principal + Interest', unit: '₹', placeholder: '15000', type: 'number' },
      { key: 'current_working_capital', label: 'Net Working Capital', unit: '₹', placeholder: '80000', type: 'number' },
      { key: 'monthly_revenue_growth_pct', label: 'Monthly Revenue Growth Rate', unit: '%', placeholder: '2.5', type: 'number' },
      { key: 'annual_interest_rate_pct', label: 'Borrowing Interest Rate', unit: '%', placeholder: '10.5', type: 'number' },
      { key: 'monthly_capex', label: 'Monthly Maintenance Capex', unit: '₹', placeholder: '5000', type: 'number' },
      { key: 'current_debt', label: 'Total Outstanding Debt', unit: '₹', placeholder: '200000', type: 'number' },
    ],
  };

  const advancedModelFields: Record<string, string[]> = {
    FINANCING_COMPARISON: ['purchase_cost', 'monthly_operating_gain', 'available_cash', 'loan_interest_rate_pct', 'loan_term_months', 'lease_monthly_payment', 'lease_term_months', 'equity_injection', 'discount_rate_pct'],
    BUSINESS_EXPANSION: ['expansion_capex', 'projected_monthly_revenue', 'gross_margin_pct', 'projected_monthly_opex', 'available_cash', 'committed_financing', 'financing_mode'],
    INVENTORY_PROCUREMENT: ['unit_cost', 'order_quantity', 'monthly_demand', 'current_stock', 'reorder_threshold', 'holding_cost_per_unit_month', 'stockout_cost_per_unit', 'supplier_lead_time_days'],
    CUSTOMER_CREDIT_RISK: ['customer_name', 'current_receivable', 'credit_limit', 'requested_sale_amount', 'average_monthly_sales', 'gross_margin_pct', 'default_risk_pct', 'annual_cost_of_capital_pct', 'proposed_terms_days', 'overdue_days'],
    COST_REDUCTION: ['cost_category', 'current_monthly_cost', 'proposed_monthly_cost', 'one_time_implementation_cost', 'expected_quality_cost_monthly', 'evaluation_months'],
    CASH_FLOW_PRESSURE: ['cash_balance', 'monthly_cash_inflows', 'monthly_cash_outflows', 'receivables_due_30d', 'receivables_collectible_amount', 'payables_due_30d', 'payables_deferral_amount', 'credit_line_available', 'credit_line_draw_amount', 'credit_line_interest_pct', 'monthly_survival_threshold'],
    BUSINESS_VIABILITY: ['current_monthly_revenue', 'variable_cost_pct', 'monthly_fixed_costs', 'cash_balance', 'monthly_debt_service', 'current_working_capital', 'monthly_revenue_growth_pct', 'annual_interest_rate_pct', 'monthly_capex', 'current_debt'],
    LOCATION_SELECTION: ['candidates[]: location_name, fitout_capex, monthly_rent, monthly_staff_cost, catchment_monthly_demand, conversion_rate_pct, average_order_value, gross_margin_pct, cannibalization_pct'],
  };

  const handleModelChange = (modelKey: string) => {
    setSelectedModel(modelKey);
    setDecisionTitle('');
    setEvaluation(null);
    setVersionHistory([]);
    setAdvancedForm({});
  };

  const getParameters = () => {
    const moneyInput = (value: string) => value.trim() || null;
    const numericInput = (value: string, divisor = 1) => value.trim() ? Number(value) / divisor : null;
    const textInput = (value: string) => value.trim() || null;
    switch (selectedModel) {
      case 'MACHINE_OR_EQUIPMENT_PURCHASE':
        return {
          machine_name: textInput(machineName),
          machine_cost: moneyInput(machineCost),
          down_payment: moneyInput(machineDownPayment),
          loan_interest_rate_pct: numericInput(loanInterestRate),
          loan_tenure_months: numericInput(loanTenureMonths),
          monthly_maintenance: moneyInput(monthlyMaintenance),
          current_monthly_volume: numericInput(currentMonthlyVolume),
          capacity_monthly_volume: numericInput(capacityMonthlyVolume),
          unit_price: moneyInput(equipmentUnitPrice),
          unit_variable_cost: moneyInput(equipmentVariableCost),
        };

      case 'NEW_PRODUCT_ADDITION':
        return {
          product_name: textInput(productName),
          selling_price: moneyInput(productSellingPrice),
          variable_cost: moneyInput(productVariableCost),
          expected_monthly_volume: numericInput(productMonthlyVolume),
          setup_cost: moneyInput(productSetupCost),
          cannibalization_rate: numericInput(productCannibalizationRate, 100),
        };

      case 'SUPPLIER_SWITCH_OR_CREDIT_TERMS':
        return {
          new_supplier_name: textInput(supplierName),
          current_unit_price: moneyInput(supplierCurrentPrice),
          new_unit_price: moneyInput(supplierNewPrice),
          monthly_units: numericInput(supplierMonthlyUnits),
          current_credit_days: numericInput(supplierCurrentCreditDays),
          new_credit_days: numericInput(supplierNewCreditDays),
          switching_cost: moneyInput(supplierSwitchingCost),
        };

      case 'BULK_DISCOUNT_VS_STORAGE_COST':
        return {
          regular_unit_price: moneyInput(bulkRegularPrice),
          discounted_unit_price: moneyInput(bulkDiscountedPrice),
          order_quantity: numericInput(bulkOrderQty),
          monthly_consumption: numericInput(bulkMonthlyConsumption),
          monthly_storage_per_unit: moneyInput(bulkStorageCostPerUnit),
          annual_cost_of_capital_pct: numericInput(bulkCostOfCapital),
        };

      case 'NEW_BRANCH_OR_LOCATION_OPENING':
        return {
          location_name: textInput(branchLocationName),
          fitout_capex: moneyInput(branchFitoutCapex),
          security_deposit: moneyInput(branchSecurityDeposit),
          monthly_rent: moneyInput(branchMonthlyRent),
          monthly_staff_cost: moneyInput(branchMonthlyStaffCost),
          monthly_utilities: moneyInput(branchMonthlyUtilities),
          expected_daily_customers: numericInput(branchDailyCustomers),
          average_order_value: moneyInput(branchAvgOrderValue),
          gross_margin_pct: numericInput(branchGrossMarginPct),
        };

      case 'HIRING_STAFF_OR_COMMISSION':
        return {
          role_title: textInput(staffRoleTitle),
          monthly_fixed_salary: moneyInput(staffMonthlySalary),
          commission_pct: numericInput(staffCommissionPct),
          benefits_and_overhead: moneyInput(staffBenefitsOverhead),
          expected_incremental_revenue: moneyInput(staffExpectedRevenue),
          gross_margin_pct: numericInput(staffGrossMarginPct),
        };

      case 'CREDIT_TERM_EXTENSION_TO_CUSTOMER':
        return {
          customer_name: textInput(creditCustomerName),
          current_monthly_sales: moneyInput(creditCurrentMonthlySales),
          expected_sales_increase_pct: numericInput(creditExpectedGrowthPct),
          current_terms_days: numericInput(creditCurrentTermsDays),
          proposed_terms_days: numericInput(creditProposedTermsDays),
          gross_margin_pct: numericInput(creditGrossMarginPct),
          default_risk_pct: numericInput(creditDefaultRiskPct),
          annual_cost_of_capital_pct: numericInput(creditCostOfCapitalPct),
        };

      case 'PRICE_INCREASE_OR_DISCOUNT':
        return {
          product_name: textInput(priceProductName),
          current_price: moneyInput(priceCurrentPrice),
          proposed_price: moneyInput(priceProposedPrice),
          current_monthly_volume: numericInput(priceCurrentVolume),
          unit_variable_cost: moneyInput(priceUnitVariableCost),
          price_elasticity_of_demand: numericInput(priceElasticity),
        };

      default:
        return { title: decisionTitle };
    }
  };

  const handleEvaluate = async () => {
    try {
      if (!decisionTitle.trim()) {
        toast.error('Enter a decision brief title.');
        return;
      }
      let paramsPayload: any = getParameters();
      if (selectedModel === 'LOCATION_SELECTION') {
        if (!locationCandidates.length) {
          toast.error('Add at least one location candidate.');
          return;
        }
        paramsPayload = {
          candidates: locationCandidates.map((c) => ({
            location_name: c.location_name || 'Candidate Location',
            fitout_capex: c.fitout_capex || '100000',
            monthly_rent: c.monthly_rent || '15000',
            monthly_staff_cost: c.monthly_staff_cost || '12000',
            catchment_monthly_demand: c.catchment_monthly_demand || '800',
            conversion_rate_pct: c.conversion_rate_pct || '5',
            average_order_value: c.average_order_value || '500',
            gross_margin_pct: c.gross_margin_pct || '40',
            cannibalization_pct: c.cannibalization_pct || '5',
          })),
        };
      } else if (advancedModelSpecs[selectedModel]) {
        const payload: Record<string, any> = {};
        for (const spec of advancedModelSpecs[selectedModel]) {
          const val = advancedForm[spec.key] !== undefined && advancedForm[spec.key] !== ''
            ? advancedForm[spec.key]
            : spec.placeholder || '';
          payload[spec.key] = val;
        }
        paramsPayload = payload;
      }
      const missing = Object.entries(paramsPayload).filter(([k, value]) => k !== 'candidates' && (value === null || value === undefined || value === ''));
      if (missing.length) {
        toast.error(`Enter every assumption for this model: ${missing.map(([key]) => key.replaceAll('_', ' ')).join(', ')}.`);
        return;
      }
      setEvaluating(true);
      const res = await businessApi.evaluateDecision(businessId, {
        model_type: selectedModel,
        decision_title: decisionTitle,
        parameters: paramsPayload,
        parent_decision_id: evaluation?.evaluation_id || undefined,
      });
      setEvaluation(res);
      businessApi.getDecisionHistory(businessId).then(setHistory).catch(() => undefined);
      const resOutcome = res.status || res.alternatives?.[0]?.outcome || 'EVALUATED';
      setHistory((prev) => [
        {
          id: res.evaluation_id,
          title: decisionTitle,
          model: selectedModel,
          outcome: resOutcome,
          date: new Date().toLocaleDateString('en-IN'),
        },
        ...prev.slice(0, 9),
      ]);
      toast.success(`Evaluation complete: ${resOutcome}`, 'Deterministic Engine');
      // Automatically run Monte Carlo and Sensitivity simulations
      runMonteCarlo(paramsPayload);
      runSensitivity(paramsPayload);
    } catch (err: any) {
      toast.error(`Decision evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  const runMonteCarlo = async (paramsOverride?: any) => {
    try {
      setSimulating(true);
      const mcRes = await businessApi.simulateDecisionRisk(businessId, {
        model_type: selectedModel,
        parameters: paramsOverride || getParameters(),
        iterations: 1000,
      });
      setMonteCarlo(mcRes);
    } catch (err: any) {
      console.error('Monte Carlo failed', err);
    } finally {
      setSimulating(false);
    }
  };

  const runSensitivity = async (paramsOverride?: any) => {
    try {
      setSensitivityLoading(true);
      const sensRes = await businessApi.evaluateDecisionSensitivity(businessId, {
        model_type: selectedModel,
        parameters: paramsOverride || getParameters(),
      });
      setSensitivity(sensRes);
    } catch (err: any) {
      console.error('Sensitivity analysis failed', err);
    } finally {
      setSensitivityLoading(false);
    }
  };

  const formatCurrency = (val: number | undefined | null) => {
    if (val === undefined || val === null || !Number.isFinite(Number(val))) return '—';
    return `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (val: number | undefined | null) => {
    if (val === undefined || val === null || !Number.isFinite(Number(val))) return '—';
    const num = Number(val);
    if (num > 999) return '> 999%';
    if (num < -99) return '< -99%';
    return `${num.toFixed(1)}%`;
  };

  const loadVersionHistory = async (decisionId: string) => {
    try {
      setLoadingVersions(true);
      setVersionHistory(await businessApi.getDecisionVersions(businessId, decisionId));
    } catch (err: any) {
      toast.error(`Decision history could not be loaded: ${err.message}`);
    } finally {
      setLoadingVersions(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-black/[0.08]/10">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-[#0D0F17]">Decision Laboratory</h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-none bg-[#F59E0B]/20 text-[#0D0F17] border border-[#F59E0B]/40">
              Deterministic Simulation Engine
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">
            Evaluate capital investments, compare alternatives, simulate Monte Carlo risk, and export executive briefs.
          </p>
        </div>

        {evaluation && (
          <MotionButton
            type="button"
            onClick={() => downloadAuthenticatedReport(
              businessApi.getDecisionBriefPdfUrl(businessId, evaluation.evaluation_id),
              `decision-brief-${evaluation.evaluation_id}.pdf`,
            ).catch((err: Error) => toast.error(`Brief download failed: ${err.message}`))}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-xs font-semibold hover:bg-[#E9E8E2] transition-all shadow-sm"
          >
            <FileDown className="w-4 h-4 text-[#F59E0B]" />
            <span>Download 2-Page Decision Brief (PDF)</span>
          </MotionButton>
        )}
      </div>

      {/* Model Selection & Inputs */}
      <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Select Decision Model</label>
            <select
              value={selectedModel}
              onChange={(e) => handleModelChange(e.target.value)}
              className="w-full text-xs px-3 py-2.5 rounded-none border border-black/[0.08]/15 font-semibold text-[#0D0F17] focus:outline-none focus:border-[#2B4EFF]"
            >
              {modelsList.map((m) => (
                <option key={m.key} value={m.key}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Decision Brief Title</label>
            <input
              type="text"
              value={decisionTitle}
              onChange={(e) => setDecisionTitle(e.target.value)}
              placeholder="Name this decision"
              className="w-full text-xs px-3 py-2.5 rounded-none border border-black/[0.08]/15 focus:outline-none focus:border-[#2B4EFF]"
            />
          </div>
        </div>

        {/* =================================================================== */}
        {/* MODEL 1: MACHINE_OR_EQUIPMENT_PURCHASE */}
        {/* =================================================================== */}
        {selectedModel === 'MACHINE_OR_EQUIPMENT_PURCHASE' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>Machine / Equipment Purchase Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Equipment / Machine Name</label>
                <input
                  type="text"
                  value={machineName}
                  onChange={(e) => setMachineName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Total Equipment Cost (₹)</label>
                <input
                  type="number"
                  value={machineCost}
                  onChange={(e) => setMachineCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Upfront Cash Down Payment (₹)</label>
                <input
                  type="number"
                  value={machineDownPayment}
                  onChange={(e) => setMachineDownPayment(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Loan Interest Rate (% p.a.)</label>
                <input
                  type="number"
                  step="0.1"
                  value={loanInterestRate}
                  onChange={(e) => setLoanInterestRate(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Loan Tenure (Months)</label>
                <input
                  type="number"
                  value={loanTenureMonths}
                  onChange={(e) => setLoanTenureMonths(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Monthly Maintenance (₹)</label>
                <input
                  type="number"
                  value={monthlyMaintenance}
                  onChange={(e) => setMonthlyMaintenance(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Monthly Volume</label>
                <input
                  type="number"
                  value={currentMonthlyVolume}
                  onChange={(e) => setCurrentMonthlyVolume(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Capacity After Purchase (Units / Month)</label>
                <input
                  type="number"
                  value={capacityMonthlyVolume}
                  onChange={(e) => setCapacityMonthlyVolume(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Unit Selling Price (₹)</label>
                <input
                  type="number"
                  value={equipmentUnitPrice}
                  onChange={(e) => setEquipmentUnitPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Unit Variable Cost (₹)</label>
                <input
                  type="number"
                  value={equipmentVariableCost}
                  onChange={(e) => setEquipmentVariableCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 2: NEW_PRODUCT_ADDITION */}
        {/* =================================================================== */}
        {selectedModel === 'NEW_PRODUCT_ADDITION' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>New Product Line Addition Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Product Line Name</label>
                <input
                  type="text"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Selling Price per Unit (₹)</label>
                <input
                  type="number"
                  value={productSellingPrice}
                  onChange={(e) => setProductSellingPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Variable Cost per Unit (₹)</label>
                <input
                  type="number"
                  value={productVariableCost}
                  onChange={(e) => setProductVariableCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Expected Monthly Units Sold</label>
                <input
                  type="number"
                  value={productMonthlyVolume}
                  onChange={(e) => setProductMonthlyVolume(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">One-time Tooling & Setup Cost (₹)</label>
                <input
                  type="number"
                  value={productSetupCost}
                  onChange={(e) => setProductSetupCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Cannibalization of Existing Products (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={productCannibalizationRate}
                  onChange={(e) => setProductCannibalizationRate(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 3: SUPPLIER_SWITCH_OR_CREDIT_TERMS */}
        {/* =================================================================== */}
        {selectedModel === 'SUPPLIER_SWITCH_OR_CREDIT_TERMS' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>Supplier Switch & Payment Terms Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">New Supplier Name</label>
                <input
                  type="text"
                  value={supplierName}
                  onChange={(e) => setSupplierName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Unit Purchase Price (₹)</label>
                <input
                  type="number"
                  step="0.1"
                  value={supplierCurrentPrice}
                  onChange={(e) => setSupplierCurrentPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">New Supplier Unit Price (₹)</label>
                <input
                  type="number"
                  step="0.1"
                  value={supplierNewPrice}
                  onChange={(e) => setSupplierNewPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Monthly Units Procured</label>
                <input
                  type="number"
                  value={supplierMonthlyUnits}
                  onChange={(e) => setSupplierMonthlyUnits(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Credit Terms (Days)</label>
                <input
                  type="number"
                  value={supplierCurrentCreditDays}
                  onChange={(e) => setSupplierCurrentCreditDays(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Proposed Credit Terms (Days)</label>
                <input
                  type="number"
                  value={supplierNewCreditDays}
                  onChange={(e) => setSupplierNewCreditDays(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Switching & Audit Cost (₹)</label>
                <input
                  type="number"
                  value={supplierSwitchingCost}
                  onChange={(e) => setSupplierSwitchingCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 4: BULK_DISCOUNT_VS_STORAGE_COST */}
        {/* =================================================================== */}
        {selectedModel === 'BULK_DISCOUNT_VS_STORAGE_COST' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>Bulk Order Discount vs Warehousing Cost Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Regular Unit Price (₹)</label>
                <input
                  type="number"
                  value={bulkRegularPrice}
                  onChange={(e) => setBulkRegularPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Bulk Discounted Price (₹)</label>
                <input
                  type="number"
                  value={bulkDiscountedPrice}
                  onChange={(e) => setBulkDiscountedPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Order Quantity (Units)</label>
                <input
                  type="number"
                  value={bulkOrderQty}
                  onChange={(e) => setBulkOrderQty(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Monthly Consumption Rate (Units)</label>
                <input
                  type="number"
                  value={bulkMonthlyConsumption}
                  onChange={(e) => setBulkMonthlyConsumption(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Storage & Holding Cost per Unit/mo (₹)</label>
                <input
                  type="number"
                  step="0.1"
                  value={bulkStorageCostPerUnit}
                  onChange={(e) => setBulkStorageCostPerUnit(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Annual Cost of Capital (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={bulkCostOfCapital}
                  onChange={(e) => setBulkCostOfCapital(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 5: NEW_BRANCH_OR_LOCATION_OPENING */}
        {/* =================================================================== */}
        {selectedModel === 'NEW_BRANCH_OR_LOCATION_OPENING' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>New Branch / Retail Location Expansion Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Branch / Outlet Name</label>
                <input
                  type="text"
                  value={branchLocationName}
                  onChange={(e) => setBranchLocationName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Fit-out & Interior Capex (₹)</label>
                <input
                  type="number"
                  value={branchFitoutCapex}
                  onChange={(e) => setBranchFitoutCapex(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Security Deposit (₹)</label>
                <input
                  type="number"
                  value={branchSecurityDeposit}
                  onChange={(e) => setBranchSecurityDeposit(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Monthly Rent (₹)</label>
                <input
                  type="number"
                  value={branchMonthlyRent}
                  onChange={(e) => setBranchMonthlyRent(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Monthly Staff Payroll (₹)</label>
                <input
                  type="number"
                  value={branchMonthlyStaffCost}
                  onChange={(e) => setBranchMonthlyStaffCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Monthly Utilities & Overhead (₹)</label>
                <input
                  type="number"
                  value={branchMonthlyUtilities}
                  onChange={(e) => setBranchMonthlyUtilities(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Expected Daily Footfall (Customers)</label>
                <input
                  type="number"
                  value={branchDailyCustomers}
                  onChange={(e) => setBranchDailyCustomers(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Average Order Value (₹)</label>
                <input
                  type="number"
                  value={branchAvgOrderValue}
                  onChange={(e) => setBranchAvgOrderValue(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Average Gross Margin (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={branchGrossMarginPct}
                  onChange={(e) => setBranchGrossMarginPct(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 6: HIRING_STAFF_OR_COMMISSION */}
        {/* =================================================================== */}
        {selectedModel === 'HIRING_STAFF_OR_COMMISSION' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>Staff Hiring & Incentive Structure Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Role / Position Title</label>
                <input
                  type="text"
                  value={staffRoleTitle}
                  onChange={(e) => setStaffRoleTitle(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Fixed Monthly Base Salary (₹)</label>
                <input
                  type="number"
                  value={staffMonthlySalary}
                  onChange={(e) => setStaffMonthlySalary(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Sales Commission Rate (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={staffCommissionPct}
                  onChange={(e) => setStaffCommissionPct(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Benefits & Overhead Monthly (₹)</label>
                <input
                  type="number"
                  value={staffBenefitsOverhead}
                  onChange={(e) => setStaffBenefitsOverhead(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Expected Monthly Sales Generated (₹)</label>
                <input
                  type="number"
                  value={staffExpectedRevenue}
                  onChange={(e) => setStaffExpectedRevenue(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Product Gross Margin (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={staffGrossMarginPct}
                  onChange={(e) => setStaffGrossMarginPct(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 7: CREDIT_TERM_EXTENSION_TO_CUSTOMER */}
        {/* =================================================================== */}
        {selectedModel === 'CREDIT_TERM_EXTENSION_TO_CUSTOMER' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>Customer Credit Term Extension Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Key Account / Customer Name</label>
                <input
                  type="text"
                  value={creditCustomerName}
                  onChange={(e) => setCreditCustomerName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Monthly Sales (₹)</label>
                <input
                  type="number"
                  value={creditCurrentMonthlySales}
                  onChange={(e) => setCreditCurrentMonthlySales(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Expected Sales Lift (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={creditExpectedGrowthPct}
                  onChange={(e) => setCreditExpectedGrowthPct(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Terms (Days)</label>
                <input
                  type="number"
                  value={creditCurrentTermsDays}
                  onChange={(e) => setCreditCurrentTermsDays(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Proposed Extended Terms (Days)</label>
                <input
                  type="number"
                  value={creditProposedTermsDays}
                  onChange={(e) => setCreditProposedTermsDays(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Gross Margin on Products (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={creditGrossMarginPct}
                  onChange={(e) => setCreditGrossMarginPct(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Estimated Default Risk (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={creditDefaultRiskPct}
                  onChange={(e) => setCreditDefaultRiskPct(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* MODEL 8: PRICE_INCREASE_OR_DISCOUNT */}
        {/* =================================================================== */}
        {selectedModel === 'PRICE_INCREASE_OR_DISCOUNT' && (
          <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>Price Elasticity & Demand Sensitivity Assumptions</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Target Product / Service Name</label>
                <input
                  type="text"
                  value={priceProductName}
                  onChange={(e) => setPriceProductName(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Unit Price (₹)</label>
                <input
                  type="number"
                  value={priceCurrentPrice}
                  onChange={(e) => setPriceCurrentPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Proposed Adjusted Price (₹)</label>
                <input
                  type="number"
                  value={priceProposedPrice}
                  onChange={(e) => setPriceProposedPrice(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Current Monthly Volume (Units)</label>
                <input
                  type="number"
                  value={priceCurrentVolume}
                  onChange={(e) => setPriceCurrentVolume(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Unit Variable Cost (₹)</label>
                <input
                  type="number"
                  value={priceUnitVariableCost}
                  onChange={(e) => setPriceUnitVariableCost(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Price Elasticity of Demand (e.g. -1.1)</label>
                <input
                  type="number"
                  step="0.1"
                  value={priceElasticity}
                  onChange={(e) => setPriceElasticity(e.target.value)}
                  className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {selectedModel === 'LOCATION_SELECTION' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#0D0F17]">Candidate Store / Branch Locations</label>
                <p className="text-[11px] text-slate-500">Enter assumptions for each location candidate to evaluate catchment demand, rent feasibility, and payback.</p>
              </div>
              <MotionButton
                type="button"
                onClick={() => setLocationCandidates((prev) => [
                  ...prev,
                  {
                    location_name: `Candidate ${prev.length + 1}`,
                    fitout_capex: '300000',
                    monthly_rent: '25000',
                    monthly_staff_cost: '20000',
                    catchment_monthly_demand: '1000',
                    conversion_rate_pct: '5',
                    average_order_value: '600',
                    gross_margin_pct: '40',
                    cannibalization_pct: '5',
                  }
                ])}
                className="px-3 py-1.5 bg-[#FAF7F2] border border-[#231412] text-xs font-bold text-[#231412] hover:bg-[#231412] hover:text-white transition-all shadow-xs"
              >
                + Add Candidate Location
              </MotionButton>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {locationCandidates.map((cand, cIdx) => (
                <div key={cIdx} className="p-4 bg-[#FAF7F2] border-2 border-[#231412] space-y-3">
                  <div className="flex items-center justify-between border-b border-[#231412]/20 pb-2">
                    <span className="font-bold text-xs text-[#231412] uppercase font-mono">Location #{cIdx + 1}</span>
                    {locationCandidates.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setLocationCandidates((prev) => prev.filter((_, idx) => idx !== cIdx))}
                        className="text-xs text-rose-700 hover:underline font-bold"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="col-span-2">
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Location Name</label>
                      <input
                        type="text"
                        value={cand.location_name}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, location_name: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Fitout Capex (₹)</label>
                      <input
                        type="number"
                        value={cand.fitout_capex}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, fitout_capex: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Monthly Rent (₹)</label>
                      <input
                        type="number"
                        value={cand.monthly_rent}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, monthly_rent: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Monthly Staff Cost (₹)</label>
                      <input
                        type="number"
                        value={cand.monthly_staff_cost}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, monthly_staff_cost: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Monthly Demand (Footfall)</label>
                      <input
                        type="number"
                        value={cand.catchment_monthly_demand}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, catchment_monthly_demand: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Conversion Rate (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={cand.conversion_rate_pct}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, conversion_rate_pct: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Avg Order Value (₹)</label>
                      <input
                        type="number"
                        value={cand.average_order_value}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, average_order_value: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Gross Margin (%)</label>
                      <input
                        type="number"
                        value={cand.gross_margin_pct}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, gross_margin_pct: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-[#5C403B] uppercase mb-0.5">Cannibalization (%)</label>
                      <input
                        type="number"
                        value={cand.cannibalization_pct}
                        onChange={(e) => {
                          const val = e.target.value;
                          setLocationCandidates((prev) => prev.map((item, idx) => idx === cIdx ? { ...item, cannibalization_pct: val } : item));
                        }}
                        className="w-full text-xs px-2.5 py-1 bg-white border border-[#231412] font-mono"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {selectedModel !== 'LOCATION_SELECTION' && advancedModelSpecs[selectedModel] && (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-[#0D0F17]">Model Assumptions & Parameters</label>
              <p className="text-[11px] text-slate-500">Structured parameters evaluated with 100% deterministic Python Decimal arithmetic.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {advancedModelSpecs[selectedModel].map((spec) => (
                <div key={spec.key} className="space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <label className="font-semibold text-slate-600 truncate">{spec.label}</label>
                    {spec.unit && <span className="font-mono text-[10px] font-bold text-[#C8281E] bg-[#C8281E]/10 px-1 rounded">{spec.unit}</span>}
                  </div>
                  <input
                    type={spec.type || 'text'}
                    value={advancedForm[spec.key] ?? spec.placeholder ?? ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setAdvancedForm((prev) => ({ ...prev, [spec.key]: val }));
                    }}
                    placeholder={spec.placeholder}
                    className="w-full text-xs px-3 py-1.5 rounded-none border border-black/[0.08]/15 bg-white font-mono"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="flex items-center justify-between pt-2 border-t border-black/[0.08]/10">
          <p className="text-xs text-slate-500 flex items-center space-x-1">
            <HelpCircle className="w-3.5 h-3.5 text-[#F59E0B]" />
            <span>Deterministic financial model executes 100% in Python backend with strict Decimal precision.</span>
          </p>

          <MotionButton
            onClick={handleEvaluate}
            disabled={evaluating}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-xs font-bold hover:bg-[#E9E8E2] transition-all shadow-md disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${evaluating ? 'animate-spin' : ''}`} />
            <span>{evaluating ? 'Evaluating Model...' : 'Execute Evaluation & Monte Carlo'}</span>
          </MotionButton>
        </div>
      </div>

      {/* Evaluation Results */}
      {evaluation && (
        <div className="space-y-6">
          {/* Recommendation Banner */}
          {(() => {
            const outcome = evaluation.status || evaluation.alternatives?.[0]?.outcome || 'EVALUATED';
            const isFeasible = outcome === 'FEASIBLE' || outcome === 'PROCEED';
            const isCaution = outcome === 'CAUTION' || outcome === 'CONDITIONAL';
            return (
              <div
                className={`p-6 rounded-none border shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
                  isFeasible
                    ? 'bg-[#10B981]/10 border-[#10B981]/40/30'
                    : isCaution
                    ? 'bg-[#F59E0B]/10 border-[#F59E0B]/40'
                    : 'bg-[#2B4EFF]/10 border-[#2B4EFF]/40'
                }`}
              >
                <div className="flex items-start space-x-3.5">
                  <div
                    className={`p-2 rounded-none mt-0.5 ${
                      isFeasible
                        ? 'bg-[#10B981]/10 text-[#0D0F17]'
                        : isCaution
                        ? 'bg-[#F59E0B] text-[#0D0F17]'
                        : 'bg-[#2B4EFF] text-[#0D0F17]'
                    }`}
                  >
                    {isFeasible ? (
                      <CheckCircle className="w-6 h-6" />
                    ) : (
                      <AlertTriangle className="w-6 h-6" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="font-bold text-base text-[#0D0F17]">
                        Recommendation Verdict: {outcome}
                      </h3>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-none bg-white/70 border border-black/[0.08]/10">
                        {selectedModel}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
                      {evaluation.executive_summary || 'Deterministic quantitative analysis executed across financial records.'}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="block text-[11px] text-slate-500 font-mono">Timestamp</span>
                  <span className="text-xs font-semibold text-[#0D0F17]">{new Date().toLocaleTimeString()}</span>
                </div>
              </div>
            );
          })()}

          {/* Primary Model Deterministic Calculations */}
          {evaluation.calculations && Object.keys(evaluation.calculations).length > 0 && (
            <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-4">
              <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
                <Calculator className="w-4 h-4 text-[#F59E0B]" />
                <span>Primary Financial Model Calculations & Verified Evidence Metrics</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 text-xs font-mono">
                {Object.entries(evaluation.calculations).map(([key, val]) => (
                  <div key={key} className="p-3 rounded-none bg-[#FAF7F2] border border-[#231412]/10 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase block tracking-wider truncate" title={key.replaceAll('_', ' ')}>
                      {key.replaceAll('_', ' ')}
                    </span>
                    <span className="text-sm font-bold text-[#0D0F17] block">
                      {typeof val === 'number'
                        ? (key.includes('pct') || key.includes('rate') || key.includes('margin')
                            ? `${val.toFixed(1)}%`
                            : key.includes('months') || key.includes('days') || key.includes('volume') || key.includes('units') || key.includes('count') || key.includes('dscr')
                            ? (key.includes('dscr') ? `${val.toFixed(2)}x` : val.toLocaleString('en-IN'))
                            : `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
                        : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evaluated Alternatives */}
          {evaluation.alternatives && evaluation.alternatives.length > 0 && (
            <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-4">
              <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
                <Award className="w-4 h-4 text-[#F59E0B]" />
                <span>Deterministic Financial Calculations & Alternative Outcomes</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {evaluation.alternatives.map((alt) => (
                  <div
                    key={alt.alternative_id}
                    className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-[#0D0F17]">{alt.alternative_name}</span>
                      <span
                        className={`px-2.5 py-0.5 rounded-none text-[10px] font-bold uppercase tracking-wider ${
                          alt.outcome === 'FEASIBLE'
                            ? 'bg-[#10B981]/10 text-[#10B981]'
                            : 'bg-[#F59E0B]/10 text-[#F59E0B]'
                        }`}
                      >
                        {alt.outcome} (Rank #{alt.rank})
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                      <div className="p-2 rounded-none bg-white border border-black/[0.08]/5">
                        <span className="text-[10px] text-slate-500 block">Net Present Value</span>
                        <span className="font-bold text-[#0D0F17]">{formatCurrency(alt.npv_amount)}</span>
                      </div>
                      <div className="p-2 rounded-none bg-white border border-black/[0.08]/5">
                        <span className="text-[10px] text-slate-500 block">IRR</span>
                        <span className="font-bold text-[#0D0F17]">{formatPercent(alt.irr_pct)}</span>
                      </div>
                      <div className="p-2 rounded-none bg-white border border-black/[0.08]/5">
                        <span className="text-[10px] text-slate-500 block">Payback Period</span>
                        <span className="font-bold text-[#0D0F17]">
                          {alt.payback_period_months !== null && alt.payback_period_months !== undefined
                            ? alt.payback_period_months <= 0
                              ? 'Immediate (< 1 mo)'
                              : `${alt.payback_period_months} mo`
                            : '—'}
                        </span>
                      </div>
                      <div className="p-2 rounded-none bg-white border border-black/[0.08]/5">
                        <span className="text-[10px] text-slate-500 block">Monthly Cash Net</span>
                        <span className="font-bold text-[#10B981]">{formatCurrency(alt.monthly_net_cash_impact)}</span>
                      </div>
                      <div className="p-2 rounded-none bg-white border border-black/[0.08]/5">
                        <span className="text-[10px] text-slate-500 block">ROI</span>
                        <span className="font-bold text-[#0D0F17]">{formatPercent(alt.roi_pct)}</span>
                      </div>
                      <div className="p-2 rounded-none bg-white border border-black/[0.08]/5">
                        <span className="text-[10px] text-slate-500 block">Composite Score</span>
                        <span className="font-bold text-[#F59E0B]">{alt.composite_score ?? '—'}{alt.composite_score === null ? '' : '/100'}</span>
                      </div>
                    </div>

                    {alt.key_drivers && alt.key_drivers.length > 0 && (
                      <div className="text-[11px] text-slate-500">
                        <span className="font-semibold text-[#0D0F17]">Key Drivers:</span>{' '}
                        {alt.key_drivers.join(' • ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Monte Carlo Risk Simulation Results */}
          {monteCarlo && (
            <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
                  <Dices className="w-4 h-4 text-[#F59E0B]" />
                  <span>Monte Carlo Risk Simulation ({monteCarlo.iterations_run ?? 1000} Iterations)</span>
                </div>
                <span className="text-xs font-mono text-slate-500">
                  Confidence: {monteCarlo.confidence_verdict || 'STABLE'}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-none bg-white border border-black/[0.08]/10">
                  <span className="block text-[11px] text-slate-500">Downside Shortfall Risk</span>
                  <span className="text-base font-bold font-mono text-[#0D0F17]">
                    {monteCarlo.probability_of_negative_npv_pct ?? 0}%
                  </span>
                </div>
                <div className="p-3 rounded-none bg-white border border-black/[0.08]/10">
                  <span className="block text-[11px] text-slate-500">P10 Conservative Downside</span>
                  <span className="text-base font-bold font-mono text-[#0D0F17]">
                    {formatCurrency(monteCarlo.p10_worst_case_npv)}
                  </span>
                </div>
                <div className="p-3 rounded-none bg-white border border-black/[0.08]/10">
                  <span className="block text-[11px] text-slate-500">P50 Expected Median</span>
                  <span className="text-base font-bold font-mono text-[#0D0F17]">
                    {formatCurrency(monteCarlo.p50_median_npv)}
                  </span>
                </div>
                <div className="p-3 rounded-none bg-white border border-black/[0.08]/10">
                  <span className="block text-[11px] text-slate-500">P90 Optimistic Upside</span>
                  <span className="text-base font-bold font-mono text-[#0D0F17]">
                    {formatCurrency(monteCarlo.p90_best_case_npv)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Sensitivity Analysis Results */}
          {sensitivity && sensitivity.variable_swings && sensitivity.variable_swings.length > 0 && (
            <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-4">
              <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
                <BarChart3 className="w-4 h-4 text-[#F59E0B]" />
                <span>Deterministic Sensitivity & Stress Test Matrix (±10% Variable Swings)</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-black/[0.08]/10 text-slate-500 font-mono text-[11px]">
                      <th className="py-2">Variable Stressed</th>
                      <th className="py-2">Low Shock</th>
                      <th className="py-2">High Shock</th>
                      <th className="py-2">Low NPV Impact</th>
                      <th className="py-2">High NPV Impact</th>
                      <th className="py-2">Swing Range</th>
                      <th className="py-2">Elasticity Ratio</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#282623]/5 font-mono">
                    {sensitivity.variable_swings.map((f, i) => (
                      <tr key={i} className="hover:bg-white/60 transition-colors">
                        <td className="py-2 font-sans font-medium text-[#0D0F17]">{f.variable_name}</td>
                        <td className="py-2 text-slate-500">{f.low_value}</td>
                        <td className="py-2 text-slate-500">{f.high_value}</td>
                        <td className="py-2 text-[#2B4EFF] font-semibold">{formatCurrency(f.low_npv)}</td>
                        <td className="py-2 text-[#10B981] font-semibold">{formatCurrency(f.high_npv)}</td>
                        <td className="py-2 font-bold text-[#0D0F17]">{formatCurrency(f.swing_range)}</td>
                        <td className="py-2">
                          <span className="px-2 py-0.5 rounded-none text-[10px] font-bold bg-[#F59E0B]/20 text-[#0D0F17]">
                            {f.elasticity_ratio.toFixed(2)}x
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Saved History */}
          {history.length > 0 && (
            <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-3">
              <div className="flex items-center space-x-2 text-xs font-bold text-[#0D0F17] uppercase tracking-wider">
                <History className="w-4 h-4 text-[#F59E0B]" />
                <span>Saved Decision Evaluations History</span>
              </div>
              <div className="divide-y divide-[#282623]/5 text-xs">
                {history.map((h, i) => (
                  <div key={i} className="py-2 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-[#0D0F17]">{h.title}</span>
                      <span className="text-[11px] text-slate-500 ml-2">({h.model})</span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-[11px] font-mono text-slate-500">{h.date}</span>
                      <span
                        className={`px-2 py-0.5 rounded-none text-[10px] font-bold ${
                          h.outcome === 'FEASIBLE' ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-[#2B4EFF]/10 text-[#2B4EFF]'
                        }`}
                      >
                        {h.outcome}
                      </span>
                      <MotionButton
                        type="button"
                        onClick={() => loadVersionHistory(h.id)}
                        className="rounded-none border border-black/[0.08]/20 px-2 py-1 text-[10px] font-semibold text-[#0D0F17] hover:bg-[#2B4EFF]/5"
                      >
                        Versions
                      </MotionButton>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(versionHistory.length > 0 || loadingVersions) && (
            <div className="rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#0D0F17]">Decision assumption versions</h3>
                {loadingVersions && <span className="text-xs text-slate-500">Loading…</span>}
              </div>
              <div className="space-y-3">
                {versionHistory.map((version) => (
                  <article key={version.id} className="rounded-none border border-black/[0.08]/10 bg-white p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-[#0D0F17]">Version {version.version_number} · {version.outcome}</span>
                      <time className="font-mono text-slate-500">{new Date(version.created_at).toLocaleString()}</time>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{version.explanation}</p>
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer font-semibold text-[#0D0F17] hover:text-[#C8281E]">Compare inputs and outcomes</summary>
                      <div className="mt-2 grid gap-3 md:grid-cols-2">
                        <div className="bg-[#FAF7F2] p-3 border border-[#231412]/15">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-[#6E524D] mb-1.5 font-mono">Assumed Model Inputs</div>
                          <div className="space-y-1">
                            {Object.entries(version.inputs || {}).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center py-0.5 border-b border-[#231412]/10 text-xs">
                                <span className="text-[#6E524D] font-mono text-[11px]">{k.replace(/_/g, ' ')}:</span>
                                <span className="font-semibold text-[#231412] font-mono break-all text-right ml-2">
                                  {typeof v === 'object' && v !== null
                                    ? (Array.isArray(v) ? v.join(', ') : Object.entries(v).map(([subK, subV]) => `${subK}: ${subV}`).join('; '))
                                    : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="bg-[#FAF7F2] p-3 border border-[#231412]/15">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-[#6E524D] mb-1.5 font-mono">Computed Outcomes & Metrics</div>
                          <div className="space-y-1">
                            {Object.entries(version.calculations || {}).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center py-0.5 border-b border-[#231412]/10 text-xs">
                                <span className="text-[#6E524D] font-mono text-[11px]">{k.replace(/_/g, ' ')}:</span>
                                <span className="font-semibold text-[#231412] font-mono break-all text-right ml-2">
                                  {typeof v === 'object' && v !== null
                                    ? (Array.isArray(v) ? v.join(', ') : Object.entries(v).map(([subK, subV]) => `${subK}: ${subV}`).join('; '))
                                    : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </details>
                  </article>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
