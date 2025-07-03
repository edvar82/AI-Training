def calculate_discount(customer_type, purchase_amount, loyalty_years):
    """
    Calcula o desconto baseado no tipo de cliente, valor da compra e anos de fidelidade.
    
    Args:
        customer_type (str): Tipo do cliente ('regular', 'premium', 'vip')
        purchase_amount (float): Valor da compra
        loyalty_years (int): Anos de fidelidade do cliente
    
    Returns:
        float: Valor do desconto calculado
    """
    base_discount = 0.0
    
    # Desconto baseado no tipo de cliente
    if customer_type == 'regular':
        base_discount = 0.05  # 5%
    elif customer_type == 'premium':
        base_discount = 0.10  # 10%
    elif customer_type == 'vip':
        base_discount = 0.15  # 15%
    else:
        return 0.0  # Tipo de cliente inválido
    
    # Desconto adicional baseado nos anos de fidelidade
    loyalty_discount = min(loyalty_years * 0.01, 0.10)  # Máximo 10% adicional
    
    # Desconto adicional para compras grandes
    if purchase_amount >= 1000:
        bulk_discount = 0.05  # 5% adicional
    elif purchase_amount >= 500:
        bulk_discount = 0.03  # 3% adicional
    else:
        bulk_discount = 0.0
    
    # Calcula o desconto total (máximo 30%)
    total_discount = min(base_discount + loyalty_discount + bulk_discount, 0.30)
    
    # Calcula o valor do desconto
    discount_amount = purchase_amount * total_discount
    
    return round(discount_amount, 2)
