from .models import TDSHeading

def seed_default_tds_headings():
    """
    Seeds the standard 42 revenue codes provided by the user.
    """
    data = [
        ("11111", "Tax on income of sole proprietorship and personal income", "It includes tax levied on income of sole proprietorship and personal income."),
        ("11112", "Remuneration tax", "It includes taxes levied on income of a natural person received from various sources such as salary, wages, remuneration, allowances and benefits, pension, other payment done in relation to employment, studies and teachings."),
        ("11113", "Capital gain tax", "It includes tax levied on individuals and sole proprietorships on received capital gain by selling, leasing or transferring the ownership of house, land and shares."),
        ("11115", "Windfall gain tax", "It includes the tax levied on the income received by a person from gambling, lotteries, wagers, gifts, donations, succession, informant, reward, etc."),
        ("11119", "Other tax imposed on income of sole proprietorship", "It includes other taxes which are not covered under the above-mentioned titles."),
        ("11120", "Tax imposed on income of an entity", "It includes taxes levied upon the income of commercial entities and corporations. Tax cannot be deposited under this code."),
        ("11121", "Tax imposed on profit of an entity: Government Corporation", "It included tax levied upon the income of government entities which is either fully owned or majorly owned (more than 50%) by the government and managerial control over such entities."),
        ("11122", "Tax imposed on profit of an entity (Public Limited Company)", "It includes taxes levied on the income of any public limited company which are registered under Companies Act, and company having less than 50 percent ownership of the government."),
        ("11123", "Tax imposed on profit of an entity (Private Limited Company)", "It includes taxes levied on the income of private limited company which are registered under the Companies Act and companies specified under the Income Tax Act."),
        ("11124", "Tax imposed on profit of an entity (other institutions)", "Other than listed in the aforementioned subheadings 11121 to 11123 such as partnership firms, co-operative organizations, trust, entities foreign companies, and other entities."),
        ("11125", "Capital gain tax-Entity", "It includes the tax levied on the entity on the capital gains from various types of property, including the sale, lease, transfer of rights, etc., of houses, land, shares etc."),
        ("11126", "Windfall gain tax-Entity", "It includes the tax levied on the income received by an entity from lotteries, gifts, donations, succession, reward, etc."),
        ("11129", "Other tax imposed on income of an entity.", "Those not covered by the above-mentioned headings fall under these taxes, including other applicable taxes"),
        ("11130", "Tax imposed on income from investment and other income.", "It includes tax levied on income other than under the above-mentioned headings 11111 to 11125. Funds cannot be deposited under this heading."),
        ("11131", "Tax imposed on income from property, contract and lease", "It includes tax on income received from the rent or lease of real estate, as well as income from vehicles and other immovable property leased or placed under a long-term lease or contract."),
        ("11132", "Tax imposed on interest", "It includes tax levied upon interest paid or received from banks, finance companies or other entities or individuals."),
        ("11133", "Tax imposed on dividend.", "It includes tax levied upon dividends which are received by investing in any company."),
        ("11134", "Tax imposed on other investment related income", "It includes tax on other income related to investment."),
        ("11139", "Tax imposed on other income", "The above-mentioned title number includes taxes on incomes that are not covered"),
        ("11200", "Tax imposed on wages and salaries.", "It includes taxes based on salary and rent. This amount cannot be credited to the original title."),
        ("11211", "Social security tax based on wages and salaries.", "It includes taxes based on salary and rent. Tax cannot be credited under this main code."),
        ("11412", "Luxury Fee", "This includes tax levied upon the luxury services such as services provided by five-star or above five-star hotels, luxury resorts, imported liquor, and luxury goods and diamonds above a certain price, gold encrusted with pearls, or precious jewelry."),
        ("11442", "Health service tax", "It includes taxes on health services provided by other health institutions, excluding health services offered by the government and community hospitals"),
        ("11443", "Education service tax (Educational Institution)", "It includes the service charge on tuition fees for designated education offered by private educational institutions."),
        ("11444", "Education service tax (Foreign education)", "Students who are going to study abroad have to submit, and this includes the service fee charged on tuition fees."),
        ("11445", "Digital service tax", "It includes the tax levied on the transaction value of digital services provided by non-residents to consumers in Nepal, encompassing advertising services, movies, documents, downloads, cloud gaming, mobile apps, internet and software updates, as well as education and consulting services."),
        ("11454", "Road construction and maintenance tax", "It includes the tax to be collected at the traffic management office during vehicle registration, based on the type of vehicle to which it belongs."),
        ("14193", "Fee for international tourism", "It includes fees charged on the payment amount made by Nepali tourists traveling abroad for tourism. Such fees should be collected by the foreign tour package seller at the time of selling the package and when recording the expenses incurred by the firm or company for accompanying the natural person related to them on a foreign tour for business promotion."),
        ("14194", "Fee for foreign employment", "It includes the fee deducted, according to the law, from the amount charged by the person or organization licensed to conduct foreign employment business from individuals going for foreign employment."),
        ("14214", "Fee for communication service", "The amount of telecommunication service fee is included in this."),
        ("14215", "Fee for telephone ownership", "Telephone ownership amount is included in this."),
        ("33311", "Value added tax (Manufacturing)", "It includes the value-added tax charged when the producer manufactures and sells goods."),
        ("33313", "Value added tax (Sales and distribution of goods)", "This includes the amount payable by wholesalers and retailers as value-added tax."),
        ("33314", "Value added tax (Consultation and contract)", "It includes value-added tax on all types of contract business and consultancy services. Before the accrual tax upon death is applied, any pending contract tax that is yet to be collected should be deposited within this."),
        ("33315", "Value added tax (Tourism service)", "It includes the value-added tax levied on hotels, travel agencies, and businesses related to tourism such as hiking (trekking) and boating (rafting). Before the implementation of the value-added tax, any remaining hotel tax, if collected, should be deposited within this."),
        ("33316", "Value added tax (Communication services, insurance, aviation and other collection of services)", "It includes value-added tax and air flight tax levied on the sale of all types of communication services (except government postal services), insurance, and other specified services. If the entertainment tax is due before the implementation of value-added tax, it should be deposited within this"),
        ("33317", "Value added tax (collected from unregistered person)", "It comprises the value-added tax collected when availing services from an unregistered person outside Nepal, the value-added tax imposed on the sale of wood, and the value-added tax collected or filed by local levels, international organizations, missions, governments in Nepal, or public institutions dealing in goods not subject to value-added tax. The tax is already included."),
        ("33331", "Excise duty (Tobacco)", "It includes excise duty levied on the production of all types of tobacco products."),
        ("33332", "Excise duty (Alcohol)", "It includes excise duty levied on the production of alcohol (including wine and soft drinks)"),
        ("33333", "Excise duty (Beer)", "It includes excise duty levied on the production of beer."),
        ("33334", "Excise duty (Other industrial products)", "It includes excise duties on industrial products other than those mentioned in sub-headings 33331, 33332 and 33333."),
    ]
    
    for code, name, description in data:
        TDSHeading.objects.get_or_create(
            code=code,
            defaults={'name': name, 'description': description}
        )
