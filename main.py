import sys

from youtube_analyzer.core.normalizer import TopicNormalizer


def main():
    seed = sys.argv[1] if len(sys.argv) > 1 else "Google Ads untuk UMKM"
    canonical_id = TopicNormalizer.generate_canonical_id(seed)
    surfaces = TopicNormalizer.expand_seed_surfaces(seed)

    print("=" * 60)
    print(f"Topic       : {seed}")
    print(f"Canonical ID: {canonical_id}")
    print("=" * 60)
    for platform, terms in surfaces.items():
        print(f"\n[{platform.value.upper()}]")
        for t in terms:
            intent = TopicNormalizer.classify_intent(t)
            print(f"  * {t:<40} -> [Intent: {intent.value}]")


if __name__ == "__main__":
    main()
