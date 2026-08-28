"""Seed the DB with the 8 investigations (metadata only; body_ar to be filled via admin)."""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "investigations.db"

SEED = [
    {
        "slug": "regeni-2016", "year": 2016, "date": "2016-02-26", "sort_order": 100,
        "title_ar": "«جوليو ريجيني».. حقائق مبعثرة .. اختفاءٌ فتعذيبٌ فقتلٌ .. قصة حياة إيطالي في القاهرة",
        "publication_ar": "المصري اليوم · تحقيق مطوّل",
        "title_en": "Giulio Regeni — Scattered Facts: A Disappearance, Torture, and Murder",
        "publication_en": "Al-Masry Al-Youm · Long-form investigation",
        "source_url": "https://www.almasryalyoum.com/news/details/899989",
    },
    {
        "slug": "snipers-2011", "year": 2011, "date": "2011-09-14", "sort_order": 90,
        "title_ar": "«المصري اليوم» تثبت فى تحقيق استقصائى: وزارة الداخلية استخدمت قناصة لقتل الثوار",
        "publication_ar": "المصري اليوم · تحقيق استقصائي",
        "title_en": "The Interior Ministry Used Snipers to Kill Protesters",
        "publication_en": "Al-Masry Al-Youm · Long-form investigation",
        "source_url": "https://www.almasryalyoum.com/news/details/110626",
    },
    {
        "slug": "marg-prison-2011", "year": 2011, "date": "2011-05-01", "sort_order": 80,
        "title_ar": "«المصرى اليوم» تكشف القصة الكاملة لهروب عناصر «حماس» و«حزب الله» من سجن المرج",
        "publication_ar": "المصري اليوم · تحقيق استقصائي · جائزة أريج للربيع العربي",
        "title_en": "The Full Story of the Hamas and Hezbollah Escape from Al-Marg Prison",
        "publication_en": "Al-Masry Al-Youm · ARIJ Arab Spring Award",
        "source_url": "https://www.almasryalyoum.com/news/details/129006",
    },
    {
        "slug": "sinai-mada-2017", "year": 2017, "date": "2017-05-12", "sort_order": 70,
        "title_ar": "من مفكرة صحفي في مهمة إلى سيناء: مع «مطاريد البدو» الذين أصبحوا «كتيبة الترابين»",
        "publication_ar": "مدى مصر",
        "title_en": "From a Reporter's Notebook: On Assignment in Sinai",
        "publication_en": "Mada Masr · With the Bedouin fugitives who became the \"Tarabin Brigade\"",
        "source_url": "https://www.madamasr.com/2017/05/12/feature/%d8%b3%d9%8a%d8%a7%d8%b3%d8%a9/%d9%85%d9%86-%d9%85%d9%81%d9%83%d8%b1%d8%a9-%d8%b5%d8%ad%d9%81%d9%8a-%d9%81%d9%8a-%d9%85%d9%87%d9%85%d8%a9-%d8%a5%d9%84%d9%89-%d8%b3%d9%8a%d9%86%d8%a7%d8%a1-%d9%85%d8%b9-%d9%85%d8%b7%d8%a7/",
    },
    {
        "slug": "arish-police-2013", "year": 2013, "date": "2013-07-28", "sort_order": 60,
        "title_ar": "«في انتظار الحفلة».. ليلة في قسم شرطة بالعريش يهاجمه المسلحون يوميًا",
        "publication_ar": "المصري اليوم · تحقيق ميداني",
        "title_en": "Waiting for the Party: A Night in an Al-Arish Police Station Under Daily Attack",
        "publication_en": "Al-Masry Al-Youm · Field investigation",
        "source_url": "https://www.almasryalyoum.com/news/details/241989",
    },
    {
        "slug": "rural-flood-2014", "year": 2014, "date": "2014-04-10", "sort_order": 50,
        "title_ar": "السيل الريفى.. قصة خروج الظفر من اللحم",
        "publication_ar": "المصري اليوم",
        "title_en": "The Rural Flood: How the Nail Came Out of the Flesh",
        "publication_en": "Al-Masry Al-Youm",
        "source_url": "https://www.almasryalyoum.com/news/details/426844",
    },
    {
        "slug": "sinai-bedouins-2010", "year": 2010, "date": "2010-07-04", "sort_order": 40,
        "title_ar": "«المصري اليوم» تعيش يوماً مع المطلوبين أمنياً من بدو سيناء",
        "publication_ar": "المصري اليوم · تحقيق ميداني",
        "title_en": "A Day with Sinai's Most Wanted Bedouins",
        "publication_en": "Al-Masry Al-Youm · Field investigation",
        "source_url": "https://www.almasryalyoum.com/news/details/24372",
    },
    {
        "slug": "poorest-villages-2010", "year": 2010, "date": "2010-05-19", "sort_order": 30,
        "title_ar": "«المصري اليوم» فى القرى الأكثر فقراً بعد عامين من زيارات «جمال مبارك»: ماذا تحقق؟!",
        "publication_ar": "المصري اليوم · تحقيق تنموي",
        "title_en": "Egypt's Poorest Villages, Two Years After Gamal Mubarak's Visits: What Was Delivered?",
        "publication_en": "Al-Masry Al-Youm · Development investigation",
        "source_url": "https://www.almasryalyoum.com/news/details/1865572",
    },
]

def seed():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    for item in SEED:
        existing = conn.execute("SELECT id FROM investigations WHERE slug = ?", (item["slug"],)).fetchone()
        if existing:
            print(f"skip (exists): {item['slug']}")
            continue
        conn.execute("""
            INSERT INTO investigations (slug, year, date, sort_order, published,
                title_ar, publication_ar,
                title_en, publication_en,
                source_url)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (
            item["slug"], item["year"], item["date"], item["sort_order"],
            item["title_ar"], item["publication_ar"],
            item.get("title_en"), item.get("publication_en"),
            item["source_url"],
        ))
        print(f"added: {item['slug']}")
    conn.commit()
    conn.close()
    print("done.")

if __name__ == "__main__":
    seed()
