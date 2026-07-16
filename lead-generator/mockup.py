"""
FindLeads — Trojan Horse Asset Generator
Creates professional mockup images for outreach emails.
"""

from PIL import Image, ImageDraw, ImageFont
import os
from typing import Optional


class MockupGenerator:
    """Generates professional mockup images for outreach."""
    
    def __init__(self):
        self.width = 800
        self.height = 500
        self.bg_color = (255, 255, 255)
        self.primary_color = (28, 43, 33)  # Dark green
        self.accent_color = (166, 62, 46)  # Brick red
        self.text_color = (51, 51, 51)  # Dark gray
        self.light_gray = (245, 245, 245)
    
    def generate_review_response_mockup(self, business_name: str, 
                                         review_text: str = "Great service!",
                                         response_text: str = "Thank you for your kind words!",
                                         output_path: str = "mockup.png") -> str:
        """
        Generate a mockup showing a review response.
        
        Args:
            business_name: Name of the business
            review_text: Sample customer review
            response_text: Sample business response
            output_path: Path to save the image
        
        Returns:
            Path to generated image
        """
        # Create image
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Header
        draw.rectangle([0, 0, self.width, 60], fill=self.primary_color)
        draw.text((20, 15), f"Review Response Preview for {business_name}", fill=(255, 255, 255))
        
        # Review card
        draw.rectangle([40, 80, self.width - 40, 220], fill=self.light_gray, outline=(200, 200, 200))
        draw.text((60, 100), "Customer Review:", fill=self.text_color)
        draw.text((60, 130), f'"{review_text}"', fill=self.text_color)
        draw.text((60, 170), "Rating: ★★★★★", fill=(255, 193, 7))  # Gold stars
        
        # Response card
        draw.rectangle([40, 240, self.width - 40, 380], fill=(240, 248, 240), outline=(200, 200, 200))
        draw.text((60, 260), "AI-Generated Response:", fill=self.primary_color)
        draw.text((60, 290), f'"{response_text}"', fill=self.text_color)
        draw.text((60, 340), "Human-like • Personalized • Professional", fill=self.accent_color)
        
        # Footer
        draw.rectangle([0, self.height - 60, self.width, self.height], fill=self.primary_color)
        draw.text((20, self.height - 45), "Powered by FindLeads", fill=(255, 255, 255))
        draw.text((self.width - 200, self.height - 45), "www.findleads.com", fill=(200, 200, 200))
        
        # Save
        img.save(output_path, quality=95)
        
        return output_path
    
    def generate_website_improvement_mockup(self, business_name: str,
                                            issues: list,
                                            output_path: str = "website_mockup.png") -> str:
        """
        Generate a mockup showing website improvement suggestions.
        
        Args:
            business_name: Name of the business
            issues: List of issues found on the website
            output_path: Path to save the image
        
        Returns:
            Path to generated image
        """
        # Create image
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Header
        draw.rectangle([0, 0, self.width, 60], fill=self.primary_color)
        draw.text((20, 15), f"Website Analysis for {business_name}", fill=(255, 255, 255))
        
        # Issues list
        y = 80
        draw.text((40, y), "Issues Found:", fill=self.accent_color)
        y += 30
        
        for i, issue in enumerate(issues[:5], 1):
            draw.text((60, y), f"{i}. {issue}", fill=self.text_color)
            y += 25
        
        # Solutions section
        y += 20
        draw.text((40, y), "How We Can Help:", fill=self.primary_color)
        y += 30
        
        solutions = [
            "Add WhatsApp button for instant customer contact",
            "Optimize website speed for better user experience",
            "Add SSL certificate for security",
            "Implement review management system",
        ]
        
        for solution in solutions:
            draw.text((60, y), f"✓ {solution}", fill=(0, 128, 0))
            y += 25
        
        # Footer
        draw.rectangle([0, self.height - 60, self.width, self.height], fill=self.primary_color)
        draw.text((20, self.height - 45), "Free Website Audit by FindLeads", fill=(255, 255, 255))
        
        # Save
        img.save(output_path, quality=95)
        
        return output_path
    
    def generate_stats_mockup(self, business_name: str,
                               review_count: int,
                               response_rate: float,
                               output_path: str = "stats_mockup.png") -> str:
        """
        Generate a mockup showing review statistics.
        
        Args:
            business_name: Name of the business
            review_count: Number of reviews
            response_rate: Response rate percentage
            output_path: Path to save the image
        
        Returns:
            Path to generated image
        """
        # Create image
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Header
        draw.rectangle([0, 0, self.width, 60], fill=self.primary_color)
        draw.text((20, 15), f"Review Analysis for {business_name}", fill=(255, 255, 255))
        
        # Stats cards
        # Card 1: Total Reviews
        draw.rectangle([40, 80, 250, 180], fill=self.light_gray, outline=(200, 200, 200))
        draw.text((60, 100), "Total Reviews", fill=self.text_color)
        draw.text((60, 130), str(review_count), fill=self.primary_color)
        
        # Card 2: Response Rate
        draw.rectangle([270, 80, 480, 180], fill=self.light_gray, outline=(200, 200, 200))
        draw.text((290, 100), "Response Rate", fill=self.text_color)
        draw.text((290, 130), f"{response_rate:.1f}%", fill=self.accent_color)
        
        # Card 3: Unanswered
        unanswered = int(review_count * (1 - response_rate / 100))
        draw.rectangle([500, 80, 710, 180], fill=self.light_gray, outline=(200, 200, 200))
        draw.text((520, 100), "Unanswered", fill=self.text_color)
        draw.text((520, 130), str(unanswered), fill=self.accent_color)
        
        # Chart placeholder
        draw.rectangle([40, 200, self.width - 40, 380], outline=(200, 200, 200))
        draw.text((300, 280), "Response Trend Chart", fill=(150, 150, 150))
        
        # Footer
        draw.rectangle([0, self.height - 60, self.width, self.height], fill=self.primary_color)
        draw.text((20, self.height - 45), "Generated by FindLeads", fill=(255, 255, 255))
        
        # Save
        img.save(output_path, quality=95)
        
        return output_path


def generate_mockup(business_name: str, mockup_type: str = "review", 
                     output_dir: str = "mockups", **kwargs) -> str:
    """
    Generate a mockup image.
    
    Args:
        business_name: Name of the business
        mockup_type: Type of mockup (review, website, stats)
        output_dir: Directory to save the mockup
        **kwargs: Additional arguments for the mockup type
    
    Returns:
        Path to generated image
    """
    generator = MockupGenerator()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    safe_name = business_name.replace(' ', '_').replace('/', '_')[:30]
    output_path = os.path.join(output_dir, f"{safe_name}_{mockup_type}.png")
    
    if mockup_type == "review":
        return generator.generate_review_response_mockup(
            business_name,
            review_text=kwargs.get('review_text', 'Great service!'),
            response_text=kwargs.get('response_text', 'Thank you for your kind words!'),
            output_path=output_path
        )
    elif mockup_type == "website":
        return generator.generate_website_improvement_mockup(
            business_name,
            issues=kwargs.get('issues', ['No WhatsApp button', 'Slow website']),
            output_path=output_path
        )
    elif mockup_type == "stats":
        return generator.generate_stats_mockup(
            business_name,
            review_count=kwargs.get('review_count', 50),
            response_rate=kwargs.get('response_rate', 10.0),
            output_path=output_path
        )
    else:
        raise ValueError(f"Unknown mockup type: {mockup_type}")


if __name__ == "__main__":
    # Test
    generator = MockupGenerator()
    
    # Generate review mockup
    generator.generate_review_response_mockup(
        "McGill Dental Center",
        review_text="Excellent service! Dr. McGill was very professional.",
        response_text="Thank you for your kind words! We're glad you had a great experience.",
        output_path="test_review_mockup.png"
    )
    print("Generated: test_review_mockup.png")
    
    # Generate website mockup
    generator.generate_website_improvement_mockup(
        "McGill Dental Center",
        issues=[
            "No WhatsApp button",
            "No contact form",
            "No social media links",
            "No blog for SEO",
        ],
        output_path="test_website_mockup.png"
    )
    print("Generated: test_website_mockup.png")
    
    # Generate stats mockup
    generator.generate_stats_mockup(
        "McGill Dental Center",
        review_count=49,
        response_rate=5.0,
        output_path="test_stats_mockup.png"
    )
    print("Generated: test_stats_mockup.png")
