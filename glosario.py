"""Qué es cada cosa: acciones, instrumentos de deuda e indicadores del entorno (texto educativo con fuente oficial)."""

SEC = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={t}&type=10-K"
BMV = ("Bolsa Mexicana de Valores (emisoras)", "https://www.bmv.com.mx/")
CNBV = ("Comisión Nacional Bancaria y de Valores", "https://www.gob.mx/cnbv")


def _bx(c):
    return ("Banco de México · SIE, cuadro " + c,
            f"https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?sector=22&accion=consultarCuadro&idCuadro={c}&locale=es")


ACCIONES = {
    "WALMEX.MX": {
        "que_es": "Walmart de México y Centroamérica opera autoservicios, tiendas de descuento (Bodega Aurrerá) y clubes de precio (Sam's Club). "
                  "Es una de las empresas de consumo más grandes del país y cotiza en la Bolsa Mexicana de Valores.",
        "que_la_mueve": "El consumo de los hogares, la inflación de alimentos, los salarios, la competencia y el tipo de cambio (parte de la mercancía es importada).",
        "fuente": BMV},
    "AMXB.MX": {
        "que_es": "América Móvil es una empresa de telecomunicaciones (telefonía móvil, internet y televisión de paga) con marcas como Telcel y Claro, "
                  "presente en México, América Latina y Europa. Aquí se sigue la serie B.",
        "que_la_mueve": "El tipo de cambio (cobra en varias monedas y tiene deuda en dólares y euros), la competencia, la inversión en redes y la regulación.",
        "fuente": BMV},
    "KOFUBL.MX": {
        "que_es": "Coca-Cola FEMSA es uno de los mayores embotelladores de productos Coca-Cola del mundo. Compra los concentrados a The Coca-Cola Company, "
                  "produce y distribuye las bebidas en México y otros países. No es lo mismo que The Coca-Cola Company (KO), la dueña de la marca, que cotiza en EE. UU.",
        "que_la_mueve": "El consumo de bebidas, el precio del azúcar, el PET y el aluminio, los impuestos a bebidas azucaradas y el tipo de cambio.",
        "fuente": BMV},
    "KIMBERA.MX": {
        "que_es": "Kimberly-Clark de México fabrica y vende productos de consumo (papel higiénico, pañales, toallas femeninas, pañuelos) "
                  "con marcas como Kleenex, Huggies y Kotex. Aquí se sigue la serie A.",
        "que_la_mueve": "El precio de la celulosa y de la energía, el tipo de cambio (varios insumos se pagan en dólares) y el consumo.",
        "fuente": BMV},
    "OMAB.MX": {
        "que_es": "Grupo Aeroportuario del Centro Norte es un concesionario que opera aeropuertos del centro y norte de México, entre ellos el de Monterrey. "
                  "Gana por cada pasajero y por los servicios comerciales dentro de las terminales.",
        "que_la_mueve": "El tráfico de pasajeros y el turismo, las tarifas aeroportuarias reguladas y el tipo de cambio (una parte de sus ingresos se cobra en dólares).",
        "fuente": BMV},
    "AAPL": {
        "que_es": "Apple diseña y vende el iPhone, la Mac, el iPad y el Apple Watch, y obtiene ingresos crecientes de servicios (App Store, iCloud, Apple Music). Cotiza en el Nasdaq.",
        "que_la_mueve": "Las ventas del iPhone y el ciclo de productos, los servicios, las tasas de interés de EE. UU. (que afectan su valuación), la regulación y su cadena de suministro en Asia.",
        "fuente": ("SEC · EDGAR (reportes anuales y trimestrales)", SEC.format(t="AAPL"))},
    "MSFT": {
        "que_es": "Microsoft vende software (Windows, Office), servicios de nube (Azure), herramientas para desarrolladores y videojuegos (Xbox). Cotiza en el Nasdaq.",
        "que_la_mueve": "El crecimiento de la nube y de la inteligencia artificial, el gasto de las empresas en tecnología y las tasas de interés de EE. UU.",
        "fuente": ("SEC · EDGAR (reportes anuales y trimestrales)", SEC.format(t="MSFT"))},
    "NVDA": {
        "que_es": "NVIDIA diseña procesadores gráficos (GPU) y chips para centros de datos y aplicaciones de inteligencia artificial. Cotiza en el Nasdaq.",
        "que_la_mueve": "La inversión de las grandes empresas en infraestructura de inteligencia artificial, las restricciones de exportación de chips y el ciclo de los semiconductores.",
        "fuente": ("SEC · EDGAR (reportes anuales y trimestrales)", SEC.format(t="NVDA"))},
    "TSLA": {
        "que_es": "Tesla fabrica vehículos eléctricos, sistemas de almacenamiento de energía y paneles solares. Cotiza en el Nasdaq.",
        "que_la_mueve": "Las entregas de vehículos, los márgenes, la competencia, los apoyos fiscales y las expectativas sobre tecnología de conducción autónoma.",
        "fuente": ("SEC · EDGAR (reportes anuales y trimestrales)", SEC.format(t="TSLA"))},
    "KO": {
        "que_es": "The Coca-Cola Company es la dueña de la marca Coca-Cola y de un portafolio de bebidas. Vende concentrados y jarabes a embotelladores, "
                  "entre ellos Coca-Cola FEMSA. Cotiza en la Bolsa de Nueva York (NYSE).",
        "que_la_mueve": "El consumo mundial de bebidas, la fortaleza del dólar (gran parte de sus ingresos son en otras monedas), los dividendos y las tasas de interés (se considera una acción defensiva).",
        "fuente": ("SEC · EDGAR (reportes anuales y trimestrales)", SEC.format(t="KO"))},
}

DEUDA = {
    "CETES 28 días": {
        "que_es": "Los Certificados de la Tesorería de la Federación son títulos de deuda del Gobierno Federal que se compran con descuento y pagan su valor nominal "
                  "($10 pesos) al vencimiento, sin cupones. Se subastan cada semana; los plazos más comunes son 28, 91, 182 y 364 días. "
                  "Aquí se sigue el de 28 días. Es la referencia de tasa sin riesgo de crédito en pesos.",
        "que_lo_mueve": "La tasa objetivo de Banxico y las expectativas sobre su trayectoria, la inflación esperada y la demanda de los inversionistas.",
        "fuente": _bx("CF107")},
    "BONOS M 10 años": {
        "que_es": "Los Bonos de Desarrollo del Gobierno Federal con tasa fija pagan un cupón fijo cada seis meses y devuelven el valor nominal ($100 pesos) al vencimiento. "
                  "Se emiten a 3, 5, 10, 20 y 30 años; aquí se sigue el de 10 años. Su precio sube cuando las tasas bajan y baja cuando suben.",
        "que_lo_mueve": "La inflación esperada, la política de Banxico, el rendimiento de los bonos del Tesoro de EE. UU. y el apetito de los extranjeros por deuda mexicana.",
        "fuente": _bx("CF107")},
    "UDIBONOS 10 años": {
        "que_es": "Los Udibonos son Bonos de Desarrollo del Gobierno Federal denominados en UDIS (Unidades de Inversión), una unidad que se ajusta con la inflación. "
                  "Pagan una tasa real fija, por lo que protegen el poder adquisitivo. Aquí se sigue el de 10 años.",
        "que_lo_mueve": "La inflación observada y esperada, las tasas reales (tasa nominal menos inflación) y la demanda de instituciones como las Afores.",
        "fuente": _bx("CF107")},
    "PAPEL COMERCIAL": {
        "que_es": "El papel comercial es un pagaré de corto plazo (menos de un año) que emiten las empresas en el mercado de valores para financiarse. "
                  "Se vende con descuento y paga su valor nominal al vencimiento. Banxico publica cuánto se colocó cada semana y cuánto está vigente.",
        "que_lo_mueve": "Las tasas de corto plazo, la confianza en el emisor (su calificación crediticia) y la competencia de otros instrumentos como los certificados bursátiles.",
        "fuente": _bx("CF133")},
    "CERTIFICADOS BURSÁTILES": {
        "que_es": "Los certificados bursátiles son títulos de crédito que emiten empresas, estados, municipios y fideicomisos para financiarse en la Bolsa Mexicana de Valores. "
                  "Pueden ser de corto plazo (hasta un año) o de mediano y largo plazo, con tasa fija o variable, y tienen calificación crediticia. "
                  "Aquí se sigue la tasa promedio ponderada de los de corto plazo que Banxico publica cada semana.",
        "que_lo_mueve": "Las tasas de CETES y de la TIIE más una sobretasa por riesgo de crédito, la calificación del emisor y la liquidez del mercado.",
        "fuente": _bx("CF133")},
    "BONDES F 2 años": {
        "que_es": "Los Bondes F son Bonos de Desarrollo con tasa revisable: su cupón se ajusta periódicamente según una tasa de referencia de corto plazo (fondeo). "
                  "Por eso su precio se mantiene cerca de 100 y casi no cambia cuando las tasas suben o bajan. Aquí se sigue el de 2 años y se muestra su precio.",
        "que_lo_mueve": "La tasa de fondeo, la demanda de inversionistas que buscan protegerse de alzas de tasas y el calendario de colocaciones.",
        "fuente": _bx("CF107")},
    "BPAG28 3 años": {
        "que_es": "Los BPAG28 son Bonos de Protección al Ahorro del IPAB (Instituto para la Protección al Ahorro Bancario) que pagan intereses cada 28 días, "
                  "con una tasa de referencia más una sobretasa. El IPAB los emite para refinanciar su deuda. Aquí se muestra esa sobretasa.",
        "que_lo_mueve": "La percepción de riesgo del emisor (respaldado por el Gobierno Federal), la liquidez y la demanda de instrumentos de tasa revisable.",
        "fuente": _bx("CF115")},
}

INDICADORES = {
    "fx": ("Tipo de cambio FIX",
           "Es el tipo de cambio de pesos por dólar que Banxico determina cada día hábil a partir de cotizaciones del mercado de cambios al mayoreo; "
           "se publica en el Diario Oficial de la Federación y sirve para solventar obligaciones en dólares pagaderas en México.",
           "Cuando el FIX sube, el peso se deprecia: los activos en dólares valen más pesos y la deuda en dólares se encarece. "
           "Cuando baja, el peso se aprecia y los rendimientos de las acciones de EE. UU. medidos en pesos se reducen."),
    "tasa_obj": ("Tasa objetivo de Banxico",
                 "Es la tasa de interés interbancaria a un día que fija la Junta de Gobierno del Banco de México; es su principal instrumento de política monetaria.",
                 "Marca el piso de las tasas en pesos: los CETES, los certificados bursátiles y los créditos se mueven alrededor de ella y de las expectativas sobre su trayectoria."),
    "tiie28": ("TIIE a 28 días",
               "La Tasa de Interés Interbancaria de Equilibrio es la tasa de referencia que usan bancos y empresas para créditos y bonos de tasa variable.",
               "Si sube, encarece los créditos y eleva la tasa de los certificados bursátiles y papel comercial de tasa variable."),
    "infl_mx": ("Inflación anual en México (INPC)",
                "Es el cambio anual del Índice Nacional de Precios al Consumidor. El INEGI lo calcula y Banxico lo publica en su SIE.",
                "Es la meta de la política de Banxico; la inflación alta mantiene las tasas altas y pesa sobre los bonos de tasa fija. Los Udibonos se ajustan con ella."),
    "effr": ("Tasa efectiva de fondos federales (Fed)",
             "Es la tasa a la que los bancos de EE. UU. se prestan dinero a un día. La Reserva Federal fija su rango objetivo; la Reserva Federal de Nueva York publica la tasa efectiva.",
             "Es el costo del dinero en dólares: cuando sube, los bonos del Tesoro rinden más y el dólar tiende a atraer capital; cuando baja, favorece a las acciones y a los mercados emergentes."),
    "ust3m": ("Tesoro de EE. UU. a 3 meses",
              "Rendimiento de los bonos del Tesoro de EE. UU. a tres meses, según la curva diaria del Departamento del Tesoro.",
              "Refleja la tasa de corto plazo de EE. UU. y las expectativas inmediatas sobre la Fed."),
    "ust2y": ("Tesoro de EE. UU. a 2 años",
              "Rendimiento de los bonos del Tesoro a dos años, muy sensible a las expectativas sobre la política de la Fed.",
              "Si sube rápido, el mercado anticipa tasas altas por más tiempo, lo que suele presionar a las acciones de crecimiento y a las monedas emergentes."),
    "ust10y": ("Tesoro de EE. UU. a 10 años",
               "Rendimiento de los bonos del Tesoro a diez años: la referencia mundial de tasa libre de riesgo a largo plazo.",
               "Compite con las acciones y con los Bonos M; cuando sube, los inversionistas exigen más rendimiento a todo lo demás. El diferencial contra el Bono M a 10 años mide la prima que paga México."),
    "ust30y": ("Tesoro de EE. UU. a 30 años",
               "Rendimiento de los bonos del Tesoro a treinta años.",
               "Indica las expectativas de inflación y de déficit de largo plazo en EE. UU."),
    "infl_us": ("Inflación anual en EE. UU. (IPC-U)",
                "Es el cambio anual del índice de precios al consumidor de EE. UU., que publica la Oficina de Estadísticas Laborales (BLS).",
                "Determina cuánto puede bajar la Fed sus tasas; una inflación persistente mantiene altos los rendimientos del Tesoro y fuerte al dólar."),
    "vix": ("VIX",
            "Es el índice de volatilidad implícita del S&P 500 que publica Cboe; se le conoce como el «índice del miedo». Mide cuánta variación esperan los inversionistas en el mercado de EE. UU.",
            "Por debajo de 20 suele haber calma; por arriba de 30, estrés. Cuando se dispara, los inversionistas salen de activos riesgosos, entre ellos los mercados emergentes y el peso."),
    "sp500": ("S&P 500",
              "Índice de las 500 mayores empresas que cotizan en EE. UU.; es la referencia del mercado accionario estadounidense.",
              "Las acciones mexicanas y las de EE. UU. de esta app suelen moverse en la misma dirección que él; la correlación y la beta del periodo se muestran más abajo."),
    "nasdaq": ("Nasdaq Composite",
               "Índice de las empresas que cotizan en el Nasdaq, con mucho peso de tecnología.",
               "Resume el ánimo hacia las empresas tecnológicas (Apple, Microsoft, NVIDIA y Tesla)."),
    "dow": ("Dow Jones Industrial Average",
            "Índice de 30 grandes empresas de EE. UU.",
            "Referencia tradicional de las empresas industriales y de consumo grandes, entre ellas Coca-Cola."),
    "dxy": ("Índice dólar (DXY)",
            "Mide el valor del dólar frente a una canasta de monedas (euro, yen, libra, dólar canadiense, corona sueca y franco suizo).",
            "Un dólar fuerte suele presionar a los mercados emergentes y a las materias primas; uno débil los favorece."),
    "ipc": ("S&P/BMV IPC",
            "Índice de las acciones más líquidas de la Bolsa Mexicana de Valores; es la referencia del mercado accionario de México.",
            "Es el punto de comparación de las cinco acciones mexicanas de esta app."),
    "stoxx": ("Euro Stoxx 50", "Índice de las 50 mayores empresas de la zona euro.", "Muestra el ánimo del mercado europeo."),
    "nikkei": ("Nikkei 225", "Índice de 225 empresas de la Bolsa de Tokio.", "Muestra el ánimo del mercado japonés."),
    "ftse": ("FTSE 100", "Índice de las 100 mayores empresas de la Bolsa de Londres.", "Muestra el ánimo del mercado británico."),
    "shanghai": ("Shanghai Composite", "Índice de las acciones de la Bolsa de Shanghái.", "Muestra el ánimo del mercado chino."),
}


def guia(acciones, meta, deuda):
    """Contenido de la sección «Qué es cada cosa»."""
    ac = [{"ticker": t, "nombre": n, **meta.get(t, {}), **{k: v for k, v in ACCIONES.get(t, {}).items() if k != "fuente"},
           "fuente": {"nombre": ACCIONES[t]["fuente"][0], "url": ACCIONES[t]["fuente"][1]} if t in ACCIONES else None}
          for t, n in acciones.items()]
    de = [{"nombre": n, "codigo": d["codigo"], "emisor": d["emisor"], **{k: v for k, v in DEUDA.get(n, {}).items() if k != "fuente"},
           "fuente": {"nombre": DEUDA[n]["fuente"][0], "url": DEUDA[n]["fuente"][1]} if n in DEUDA else None}
          for n, d in deuda.items()]
    ind = [{"id": k, "nombre": v[0], "que_es": v[1], "como_afecta": v[2]} for k, v in INDICADORES.items()]
    return {"acciones": ac, "deuda": de, "indicadores": ind}
