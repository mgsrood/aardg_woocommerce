from i_modules.woocommerce import get_batch_data, extract_order_details
from i_modules.invoice import transform_order_details, create_invoice_pdf

# Function to process a single order
def single_invoice(order_ids, monta_api_url, monta_username, monta_password, wcapi, logo):

    # Create an emptu list of invoices
    all_invoices = []
    
    for order_id in order_ids:
        batch_sku_dict = get_batch_data(order_id, monta_api_url, monta_username, monta_password)
        order_details = extract_order_details(order_id, wcapi)
        invoice_data = transform_order_details(order_details, batch_sku_dict)
        pdf_buffer = create_invoice_pdf(invoice_data, logo)
        all_invoices.append((pdf_buffer, order_details))
        
    return all_invoices, order_details