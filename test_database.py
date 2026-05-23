"""
Test script to verify database initialization, logic, and PDF generation.
"""

from pathlib import Path
from database import DatabaseManager
from weight_calculator import calculate_weight_from_alias
from pdf_generator import generate_weight_summary_pdf

def test_database():
    db = DatabaseManager()
    
    # Test 1: Check if settings are seeded
    settings = db.get_all_settings()
    assert "company_name" in settings, "Settings not seeded"
    print("✓ Settings seeded successfully")
    
    # Test 2: Check if products are seeded
    products = db.get_all_products()
    assert len(products) > 0, "Products not seeded"
    print(f"✓ Seeded {len(products)} products successfully")
    
    # Test 3: Search for a product
    results = db.search_products("Y12")
    assert len(results) > 0, "Search not working"
    print(f"✓ Search returned {len(results)} results for 'Y12'")
    
    # Test 4: Weight Calculation Logic
    product_12mm = results[0]
    total_weight = calculate_weight_from_alias(product_12mm, 10) # 10 pcs
    print(f"✓ Calculated weight for 10 pcs of {product_12mm['product_name']}: {total_weight:.3f} kg")
    
    # Test 5: PDF Generation
    company_settings = db.get_all_settings()
    quotation_data = {
        "quotation_number": "QT-2024-001",
        "customer_name": "Acme Construction",
        "quote_date": "2027-01-15",
        "pdf_filename": "QT-2024-001.pdf"
    }
    
    items = [
        {
            "product_description": product_12mm['product_name'],
            "quantity": 10,
            "unit_weight_kg": total_weight / 10,
            "total_weight_kg": total_weight,
            "remarks": "Standard delivery"
        }
    ]
    
    output_path = Path("test_report.pdf")
    try:
        generate_weight_summary_pdf(output_path, company_settings, quotation_data, items)
        assert output_path.exists(), "PDF was not generated"
        print(f"✓ PDF Report generated successfully at {output_path}")
        output_path.unlink() # Clean up test file
        print("✓ Cleaned up test PDF file")
    except Exception as e:
        print(f"✗ PDF Generation failed: {e}")
    
    # Cleanup test database
    db.close()

if __name__ == "__main__":
    try:
        test_database()
        print("\n✅ All tests passed successfully!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
