"""
Script to populate the database with sample rubrics.

Creates a comprehensive essay rubric with categories for argument, evidence, and grammar.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
django.setup()

from feedback_system.models import Rubric, RubricCategory, RubricCriterion, RubricLevel


def create_essay_rubric():
    """Create a comprehensive essay rubric."""

    # Create the main rubric
    rubric = Rubric.objects.create(
        name="Comprehensive Essay Rubric",
        description="A detailed rubric for evaluating academic essays across multiple dimensions",
        assignment_type="essay",
        max_score=100,
        is_active=True
    )

    print(f"✓ Created rubric: {rubric.name}")

    # Create Argument category
    argument_category = RubricCategory.objects.create(
        rubric=rubric,
        name="Argument",
        description="Evaluates the strength and clarity of the essay's main argument",
        weight=0.40,
        order=1
    )

    # Create criteria for Argument
    thesis_criterion = RubricCriterion.objects.create(
        category=argument_category,
        name="Thesis Statement",
        description="Clarity and strength of the thesis statement",
        criterion_type="argument",
        max_points=10,
        order=1
    )

    # Create levels for thesis criterion
    RubricLevel.objects.create(
        criterion=thesis_criterion,
        level_name="excellent",
        score_range_min=9,
        score_range_max=10,
        description="Thesis is clear, specific, and compelling. It presents a strong argument that guides the entire essay.",
        feedback_template="Your thesis statement is excellent: {criteria}. It clearly establishes your argument and provides a strong foundation for your essay.",
        order=1
    )

    RubricLevel.objects.create(
        criterion=thesis_criterion,
        level_name="good",
        score_range_min=7,
        score_range_max=8,
        description="Thesis is clear and present, but could be more specific or compelling.",
        feedback_template="Your thesis statement is good: {criteria}. Consider making it more specific to strengthen your argument.",
        order=2
    )

    RubricLevel.objects.create(
        criterion=thesis_criterion,
        level_name="satisfactory",
        score_range_min=5,
        score_range_max=6,
        description="Thesis is present but vague or unclear. The argument is difficult to identify.",
        feedback_template="Your thesis statement needs improvement: {criteria}. Try to be more specific and clear about your main argument.",
        order=3
    )

    RubricLevel.objects.create(
        criterion=thesis_criterion,
        level_name="needs_improvement",
        score_range_min=1,
        score_range_max=4,
        description="Thesis is missing, extremely vague, or does not present a clear argument.",
        feedback_template="Your thesis statement needs significant improvement: {criteria}. You need to clearly state your main argument.",
        order=4
    )

    # Create argument development criterion
    argument_dev_criterion = RubricCriterion.objects.create(
        category=argument_category,
        name="Argument Development",
        description="How well the main argument is developed throughout the essay",
        criterion_type="argument",
        max_points=15,
        order=2
    )

    RubricLevel.objects.create(
        criterion=argument_dev_criterion,
        level_name="excellent",
        score_range_min=14,
        score_range_max=15,
        description="Argument is exceptionally well-developed with logical progression and depth.",
        feedback_template="Your argument development is excellent: {criteria}. Each point builds logically on the previous ones.",
        order=1
    )

    RubricLevel.objects.create(
        criterion=argument_dev_criterion,
        level_name="good",
        score_range_min=11,
        score_range_max=13,
        description="Argument is well-developed with good logical flow, though some points could be expanded.",
        feedback_template="Your argument development is good: {criteria}. Consider expanding some points for greater depth.",
        order=2
    )

    RubricLevel.objects.create(
        criterion=argument_dev_criterion,
        level_name="satisfactory",
        score_range_min=8,
        score_range_max=10,
        description="Argument is present but lacks depth or logical consistency in some areas.",
        feedback_template="Your argument development is satisfactory: {criteria}. Work on improving the logical flow between points.",
        order=3
    )

    RubricLevel.objects.create(
        criterion=argument_dev_criterion,
        level_name="needs_improvement",
        score_range_min=1,
        score_range_max=7,
        description="Argument is poorly developed, lacks coherence, or does not support the thesis.",
        feedback_template="Your argument development needs improvement: {criteria}. Focus on creating a more logical and coherent argument.",
        order=4
    )

    # Create Evidence category
    evidence_category = RubricCategory.objects.create(
        rubric=rubric,
        name="Evidence",
        description="Evaluates the quality and integration of supporting evidence",
        weight=0.35,
        order=2
    )

    # Create criteria for Evidence
    evidence_quality_criterion = RubricCriterion.objects.create(
        category=evidence_category,
        name="Evidence Quality",
        description="Quality, relevance, and sufficiency of evidence provided",
        criterion_type="evidence",
        max_points=10,
        order=1
    )

    RubricLevel.objects.create(
        criterion=evidence_quality_criterion,
        level_name="excellent",
        score_range_min=9,
        score_range_max=10,
        description="Evidence is excellent: relevant, sufficient, and from credible sources.",
        feedback_template="Your evidence quality is excellent: {criteria}. You've provided strong, relevant support for your claims.",
        order=1
    )

    RubricLevel.objects.create(
        criterion=evidence_quality_criterion,
        level_name="good",
        score_range_min=7,
        score_range_max=8,
        description="Evidence is good and relevant, though more could be added or sources could be more credible.",
        feedback_template="Your evidence quality is good: {criteria}. Consider adding more evidence or using more credible sources.",
        order=2
    )

    RubricLevel.objects.create(
        criterion=evidence_quality_criterion,
        level_name="satisfactory",
        score_range_min=5,
        score_range_max=6,
        description="Evidence is present but limited in quality, relevance, or quantity.",
        feedback_template="Your evidence quality is satisfactory: {criteria}. Work on finding more relevant and credible evidence.",
        order=3
    )

    RubricLevel.objects.create(
        criterion=evidence_quality_criterion,
        level_name="needs_improvement",
        score_range_min=1,
        score_range_max=4,
        description="Evidence is missing, irrelevant, or from questionable sources.",
        feedback_template="Your evidence quality needs improvement: {criteria}. You need to find better evidence to support your claims.",
        order=4
    )

    # Create evidence integration criterion
    evidence_integration_criterion = RubricCriterion.objects.create(
        category=evidence_category,
        name="Evidence Integration",
        description="How well evidence is integrated into the argument",
        criterion_type="evidence",
        max_points=10,
        order=2
    )

    RubricLevel.objects.create(
        criterion=evidence_integration_criterion,
        level_name="excellent",
        score_range_min=9,
        score_range_max=10,
        description="Evidence is seamlessly integrated with clear analysis and connection to arguments.",
        feedback_template="Your evidence integration is excellent: {criteria}. You effectively connect evidence to your arguments.",
        order=1
    )

    RubricLevel.objects.create(
        criterion=evidence_integration_criterion,
        level_name="good",
        score_range_min=7,
        score_range_max=8,
        description="Evidence is well integrated, though some connections could be stronger.",
        feedback_template="Your evidence integration is good: {criteria}. Work on making stronger connections between evidence and arguments.",
        order=2
    )

    RubricLevel.objects.create(
        criterion=evidence_integration_criterion,
        level_name="satisfactory",
        score_range_min=5,
        score_range_max=6,
        description="Evidence is present but not well integrated or analyzed.",
        feedback_template="Your evidence integration is satisfactory: {criteria}. Focus on analyzing how evidence supports your arguments.",
        order=3
    )

    RubricLevel.objects.create(
        criterion=evidence_integration_criterion,
        level_name="needs_improvement",
        score_range_min=1,
        score_range_max=4,
        description="Evidence is poorly integrated or simply listed without analysis.",
        feedback_template="Your evidence integration needs improvement: {criteria}. You need to better connect evidence to your arguments.",
        order=4
    )

    # Create Grammar category
    grammar_category = RubricCategory.objects.create(
        rubric=rubric,
        name="Grammar",
        description="Evaluates grammar, mechanics, and writing style",
        weight=0.25,
        order=3
    )

    # Create criteria for Grammar
    grammar_mechanics_criterion = RubricCriterion.objects.create(
        category=grammar_category,
        name="Grammar and Mechanics",
        description="Correctness of grammar, spelling, and punctuation",
        criterion_type="grammar",
        max_points=10,
        order=1
    )

    RubricLevel.objects.create(
        criterion=grammar_mechanics_criterion,
        level_name="excellent",
        score_range_min=9,
        score_range_max=10,
        description="Virtually error-free. Excellent grammar, spelling, and punctuation.",
        feedback_template="Your grammar and mechanics are excellent: {criteria}. Your writing is virtually error-free.",
        order=1
    )

    RubricLevel.objects.create(
        criterion=grammar_mechanics_criterion,
        level_name="good",
        score_range_min=7,
        score_range_max=8,
        description="Few errors that do not interfere with meaning.",
        feedback_template="Your grammar and mechanics are good: {criteria}. There are a few minor errors to address.",
        order=2
    )

    RubricLevel.objects.create(
        criterion=grammar_mechanics_criterion,
        level_name="satisfactory",
        score_range_min=5,
        score_range_max=6,
        description="Several errors that occasionally interfere with meaning.",
        feedback_template="Your grammar and mechanics are satisfactory: {criteria}. Review your work for several errors that affect clarity.",
        order=3
    )

    RubricLevel.objects.create(
        criterion=grammar_mechanics_criterion,
        level_name="needs_improvement",
        score_range_min=1,
        score_range_max=4,
        description="Frequent errors that significantly interfere with meaning.",
        feedback_template="Your grammar and mechanics need improvement: {criteria}. Significant editing is needed for clarity.",
        order=4
    )

    # Create style criterion
    style_criterion = RubricCriterion.objects.create(
        category=grammar_category,
        name="Writing Style",
        description="Clarity, flow, and academic tone of writing",
        criterion_type="style",
        max_points=10,
        order=2
    )

    RubricLevel.objects.create(
        criterion=style_criterion,
        level_name="excellent",
        score_range_min=9,
        score_range_max=10,
        description="Writing is clear, engaging, and maintains an appropriate academic tone.",
        feedback_template="Your writing style is excellent: {criteria}. Your writing is clear and maintains an appropriate academic tone.",
        order=1
    )

    RubricLevel.objects.create(
        criterion=style_criterion,
        level_name="good",
        score_range_min=7,
        score_range_max=8,
        description="Writing is generally clear with good flow, though tone could be more consistent.",
        feedback_template="Your writing style is good: {criteria}. Work on maintaining a more consistent academic tone.",
        order=2
    )

    RubricLevel.objects.create(
        criterion=style_criterion,
        level_name="satisfactory",
        score_range_min=5,
        score_range_max=6,
        description="Writing is understandable but lacks clarity or appropriate academic tone.",
        feedback_template="Your writing style is satisfactory: {criteria}. Focus on improving clarity and academic tone.",
        order=3
    )

    RubricLevel.objects.create(
        criterion=style_criterion,
        level_name="needs_improvement",
        score_range_min=1,
        score_range_max=4,
        description="Writing is unclear, informal, or difficult to follow.",
        feedback_template="Your writing style needs improvement: {criteria}. Work on clarity and maintaining an academic tone.",
        order=4
    )

    print(f"✓ Created {rubric.get_total_categories()} categories")
    print(f"✓ Created {rubric.get_total_criteria()} criteria")
    print(f"✓ Total levels in rubric: {RubricLevel.objects.filter(criterion__category__rubric=rubric).count()}")

    return rubric


def main():
    """Main function to create sample rubrics."""
    print("=" * 60)
    print("Creating Sample Rubrics")
    print("=" * 60)
    print()

    try:
        # Create the comprehensive essay rubric
        essay_rubric = create_essay_rubric()

        print()
        print("=" * 60)
        print("Sample Rubrics Created Successfully")
        print("=" * 60)
        print()
        print("Rubric Summary:")
        print(f"  Name: {essay_rubric.name}")
        print(f"  Type: {essay_rubric.assignment_type}")
        print(f"  Max Score: {essay_rubric.max_score}")
        print(f"  Categories: {essay_rubric.get_total_categories()}")
        print(f"  Criteria: {essay_rubric.get_total_criteria()}")
        print()
        print("Categories:")
        for category in essay_rubric.categories.all():
            print(f"  - {category.name} (weight: {category.weight})")
            for criterion in category.criteria.all():
                print(f"    • {criterion.name} (max: {criterion.max_points} points)")
        print()
        print("✓ Rubric system is ready for use!")
        print()
        print("API Endpoints:")
        print("  GET    /api/rubrics/ - List all rubrics")
        print("  POST   /api/rubrics/ - Create new rubric")
        print("  GET    /api/rubrics/{id}/ - Get specific rubric")
        print("  GET    /api/rubrics/stats/ - Get rubric statistics")
        print("  POST   /api/rubrics/search/ - Search rubrics")
        print()

    except Exception as e:
        print(f"✗ Error creating rubrics: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()