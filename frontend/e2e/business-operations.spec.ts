import { test, expect } from '@playwright/test';
import { apiBaseURL, archiveWorkspace, createWorkspaceSession, expectJsonStatus, isoDate } from './helpers';

test.describe('Commercial operations, khata, and general ledger', () => {
  test('purchase, stock, invoice, partial receipt, returns, and ledger reconciliation', async ({ request }) => {
    const context = await createWorkspaceSession(request, 'operations');
    const { businessId, headers } = context;
    const nonce = `${Date.now()}`;
    try {
      const supplier = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/suppliers`, {
        headers,
        data: { name: `Supplier ${nonce}`, opening_balance: '0.00' },
      }), 201);
      const customer = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/customers`, {
        headers,
        data: { name: `Customer ${nonce}`, credit_limit: '5000.00', opening_balance: '0.00' },
      }), 201);
      const product = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/products`, {
        headers,
        data: {
          sku: `E2E-${nonce}`, name: `Ledger item ${nonce}`, category: 'E2E', unit: 'pcs',
          purchase_price: '15.00', selling_price: '25.00', initial_stock: 0,
        },
      }), 201);
      const purchase = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/purchases`, {
        headers,
        data: {
          supplier_id: supplier.id, bill_number: `PO-${nonce}`, purchase_date: isoDate(), due_date: isoDate(30),
          items: [{ product_id: product.id, description: product.name, quantity: 10, unit: 'pcs', unit_price: '15.00' }],
          tax_amount: '0.00', is_cash_purchase: false,
        },
      }), 201);
      const invoice = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/invoices`, {
        headers,
        data: {
          customer_id: customer.id, invoice_number: `INV-${nonce}`, invoice_date: isoDate(), due_date: isoDate(30),
          items: [{ product_id: product.id, description: product.name, quantity: 2, unit: 'pcs', unit_price: '25.00' }],
          tax_amount: '0.00', discount_amount: '0.00', is_cash_sale: false,
        },
      }), 201);
      await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/invoices/${invoice.id}/payments`, {
        headers,
        data: { amount: '10.00', payment_date: isoDate(), payment_method: 'CASH', idempotency_key: `e2e-payment-${nonce}` },
      }), 200);
      await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/returns/sales`, {
        headers,
        data: {
          invoice_id: invoice.id, return_date: isoDate(), reason: 'E2E return',
          items: [{ product_id: product.id, quantity: 1, unit_price: '25.00' }],
        },
      }), 200);
      await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/returns/purchases`, {
        headers,
        data: {
          purchase_id: purchase.id, return_date: isoDate(), reason: 'E2E supplier return',
          idempotency_key: `e2e-purchase-return-${nonce}`,
          items: [{ purchase_item_id: purchase.items[0].id, quantity: '1.0000' }],
        },
      }), 200);

      const reconciliation = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/khata/reconcile?as_of_date=${isoDate()}`, {
        headers,
      }), 200);
      expect(reconciliation).toHaveProperty('accounts_receivable');
      expect(reconciliation).toHaveProperty('accounts_payable');
      const transactions = await expectJsonStatus(await request.get(`${apiBaseURL}/businesses/${businessId}/transactions?limit=25`, { headers }), 200);
      expect(transactions.count).toBeGreaterThan(0);
      const csv = await request.get(`${apiBaseURL}/businesses/${businessId}/transactions/export.csv`, { headers });
      expect(csv.status()).toBe(200);
      expect(csv.headers()['content-type']).toContain('text/csv');
    } finally {
      await archiveWorkspace(request, context.token, businessId);
    }
  });
});
