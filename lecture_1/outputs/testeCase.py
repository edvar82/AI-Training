import unittest

def calculate_discount(customer_type, purchase_amount, loyalty_years):
    base_discount = 0.0
    
    if customer_type == 'regular':
        base_discount = 0.05
    elif customer_type == 'premium':
        base_discount = 0.10
    elif customer_type == 'vip':
        base_discount = 0.15
    else:
        return 0.0
    
    loyalty_discount = min(loyalty_years * 0.01, 0.10)
    
    if purchase_amount >= 1000:
        bulk_discount = 0.05
    elif purchase_amount >= 500:
        bulk_discount = 0.03
    else:
        bulk_discount = 0.0
    
    total_discount = min(base_discount + loyalty_discount + bulk_discount, 0.30)
    
    discount_amount = purchase_amount * total_discount
    
    return round(discount_amount, 2)

class TestCalculateDiscount(unittest.TestCase):

    def test_regular_customer_no_loyalty_no_bulk(self):
        result = calculate_discount('regular', 100, 0)
        self.assertEqual(result, 5.0)

    def test_regular_customer_no_loyalty_bulk(self):
        result = calculate_discount('regular', 600, 0)
        self.assertEqual(result, 3.0)

    def test_regular_customer_loyalty_no_bulk(self):
        result = calculate_discount('regular', 100, 5)
        self.assertEqual(result, 5.0)

    def test_regular_customer_loyalty_bulk(self):
        result = calculate_discount('regular', 1200, 5)
        self.assertEqual(result, 6.0)

    def test_premium_customer_no_loyalty_no_bulk(self):
        result = calculate_discount('premium', 100, 0)
        self.assertEqual(result, 10.0)

    def test_premium_customer_no_loyalty_bulk(self):
        result = calculate_discount('premium', 600, 0)
        self.assertEqual(result, 6.0)

    def test_premium_customer_loyalty_no_bulk(self):
        result = calculate_discount('premium', 100, 5)
        self.assertEqual(result, 10.0)

    def test_premium_customer_loyalty_bulk(self):
        result = calculate_discount('premium', 1200, 8)
        self.assertEqual(result, 8.0)

    def test_vip_customer_no_loyalty_no_bulk(self):
        result = calculate_discount('vip', 100, 0)
        self.assertEqual(result, 15.0)

    def test_vip_customer_no_loyalty_bulk(self):
        result = calculate_discount('vip', 600, 0)
        self.assertEqual(result, 9.0)

    def test_vip_customer_loyalty_no_bulk(self):
        result = calculate_discount('vip', 100, 5)
        self.assertEqual(result, 15.0)

    def test_vip_customer_loyalty_bulk(self):
        result = calculate_discount('vip', 1200, 10)
        self.assertEqual(result, 9.0)

    def test_invalid_customer_type(self):
        result = calculate_discount('unknown', 100, 0)
        self.assertEqual(result, 0.0)

    def test_max_discount_exceeded(self):
        result = calculate_discount('vip', 1000, 30)
        self.assertEqual(result, 30.0)

    def test_edge_case_of_bulk_discount(self):
        result = calculate_discount('regular', 500, 2)
        self.assertEqual(result, 4.0)

if __name__ == '__main__':
    unittest.main()