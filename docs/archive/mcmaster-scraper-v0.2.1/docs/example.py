# Vendored in makemcmasterBOM at vendor/mcmaster_scraper/ (see vendor/mcmaster_scraper/README.md).
# Runnable wrapper: scripts/mcmaster_scraper_example.py
from mcmaster_scraper.sync_api import get_products_from_url


def main():
    """Returns a DataFrame with extension springs from McMaster-Carr that exert
    within a range of forces at a given stretch length."""
    url = "https://www.mcmaster.com/products/springs/extension-springs-1~/system-of-measurement~inch"
    data = get_products_from_url(url)

    stretch_length = 6
    min_force = 10
    max_force = 10.5

    product_type = data["Product Type"]
    length = data["Lg."]
    extended_length = data["Extended Lg. @ Max. Load"]
    spring_rate = data["Spring Rate,  lbf/in"]

    displacement = stretch_length - length
    force = spring_rate * displacement

    filtered = data[
        (product_type == "Extension Springs")
        & (length < stretch_length)
        & (stretch_length < extended_length)
        & (force.between(min_force, max_force))
    ]
    return filtered[["Part Number", "Price"]]


if __name__ == "__main__":
    print(main())
