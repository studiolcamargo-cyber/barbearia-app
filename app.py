from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Barbearia - Controle Diário",
    page_icon="💈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .main { padding: 1rem; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)


# --- BANCO DE DADOS (SQLite Local) ---
def conectar_bd():
    conn = sqlite3.connect("barbearia.db", check_same_thread=False)
    cursor = conn.cursor()

    # Tabela principal de lançamentos
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            cliente TEXT NOT NULL,
            servico TEXT,
            valor REAL NOT NULL,
            valor_servicos REAL DEFAULT 0.0,
            bebidas TEXT DEFAULT '',
            valor_bebidas REAL DEFAULT 0.0,
            valor_total REAL DEFAULT 0.0,
            forma_pagamento TEXT NOT NULL
        )
    """
    )

    # Migração automática de colunas se o banco já existia
    cursor.execute("PRAGMA table_info(lancamentos)")
    colunas_existentes = [coluna[1] for coluna in cursor.fetchall()]

    if "valor_servicos" not in colunas_existentes:
        cursor.execute("ALTER TABLE lancamentos ADD COLUMN valor_servicos REAL DEFAULT 0.0")
    if "bebidas" not in colunas_existentes:
        cursor.execute("ALTER TABLE lancamentos ADD COLUMN bebidas TEXT DEFAULT ''")
    if "valor_bebidas" not in colunas_existentes:
        cursor.execute("ALTER TABLE lancamentos ADD COLUMN valor_bebidas REAL DEFAULT 0.0")
    if "valor_total" not in colunas_existentes:
        cursor.execute("ALTER TABLE lancamentos ADD COLUMN valor_total REAL DEFAULT 0.0")
        cursor.execute("UPDATE lancamentos SET valor_total = valor WHERE valor_total = 0.0")

    # Tabela de serviços
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            preco_padrao REAL NOT NULL
        )
    """
    )

    # Tabela de bebidas/produtos
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bebidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            preco_padrao REAL NOT NULL
        )
    """
    )

    # Inserção de dados padrão se estiver vazio
    cursor.execute("SELECT COUNT(*) FROM servicos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO servicos (nome, preco_padrao) VALUES (?, ?)",
            [
                ("Corte Masculino", 35.0),
                ("Barba", 25.0),
                ("Pezinho / Acabamento", 15.0),
                ("Sobrancelha", 15.0),
                ("Platinado / Pintura", 80.0),
            ],
        )

    cursor.execute("SELECT COUNT(*) FROM bebidas")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO bebidas (nome, preco_padrao) VALUES (?, ?)",
            [
                ("Cerveja Heineken", 12.0),
                ("Cerveja Amstel", 8.0),
                ("Refrigerante Lata", 6.0),
                ("Água mineral", 4.0),
                ("Energético", 15.0),
            ],
        )

    conn.commit()
    return conn


conn = conectar_bd()
cursor = conn.cursor()

# --- CABEÇALHO ---
st.title("💈 Controle da Barbearia")

# --- ABAS DO APLICATIVO ---
aba1, aba2, aba3 = st.tabs(
    ["➕ Novo Atendimento", "📊 Fechamento do Dia", "⚙️ Cadastros & Preços"]
)

# ==========================================
# ABA 1: LANÇAMENTO DE ATENDIMENTO
# ==========================================
with aba1:
    st.subheader("Registrar Atendimento")

    cursor.execute("SELECT nome, preco_padrao FROM servicos ORDER BY nome")
    servicos_db = cursor.fetchall()
    mapa_servicos = {s[0]: s[1] for s in servicos_db}

    cursor.execute("SELECT nome, preco_padrao FROM bebidas ORDER BY nome")
    bebidas_db = cursor.fetchall()
    mapa_bebidas = {b[0]: b[1] for b in bebidas_db}

    data_atendimento = st.date_input("Data do Atendimento", datetime.today())
    cliente = st.text_input("Nome do Cliente", placeholder="Ex: João Silva")

    st.divider()
    st.markdown("### ✂️ Serviços")

    servicos_selecionados = st.multiselect(
        "Selecione os Serviços Realizados",
        options=list(mapa_servicos.keys()),
        placeholder="Corte, Barba, etc.",
    )
    subtotal_servicos = sum(mapa_servicos[s] for s in servicos_selecionados)

    st.divider()
    st.markdown("### 🍺 Bebidas & Consumo")

    bebidas_selecionadas = st.multiselect(
        "Selecione as Bebidas Consumidas",
        options=list(mapa_bebidas.keys()),
        placeholder="Cerveja, Água, Refri...",
    )

    qtdes_bebidas = {}
    subtotal_bebidas = 0.0

    if bebidas_selecionadas:
        cols = st.columns(len(bebidas_selecionadas))
        for idx, beb in enumerate(bebidas_selecionadas):
            with cols[idx % len(cols)]:
                qtd = st.number_input(
                    f"Qtd: {beb}",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"qtd_{beb}",
                )
                qtdes_bebidas[beb] = qtd
                subtotal_bebidas += mapa_bebidas[beb] * qtd

    st.divider()

    total_geral_sugerido = subtotal_servicos + subtotal_bebidas

    c1, c2, c3 = st.columns(3)
    c1.metric("Serviços", f"R$ {subtotal_servicos:.2f}")
    c2.metric("Bebidas", f"R$ {subtotal_bebidas:.2f}")
    c3.metric("Total Geral", f"R$ {total_geral_sugerido:.2f}")

    col_val, col_pag = st.columns([1, 1])
    with col_val:
        valor_final = st.number_input(
            "Valor Final a Cobrar (R$)",
            min_value=0.0,
            value=float(total_geral_sugerido),
            step=5.0,
            help="Altere apenas se for dar desconto.",
        )

    with col_pag:
        forma_pagamento = st.selectbox(
            "Forma de Pagamento",
            ["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"],
        )

    if st.button("✅ Confirmar e Salvar Atendimento"):
        if not cliente.strip():
            st.error("Por favor, digite o nome do cliente.")
        elif not servicos_selecionados and not bebidas_selecionadas:
            st.error("Selecione pelo menos um serviço ou uma bebida.")
        elif valor_final <= 0:
            st.error("Informe um valor válido.")
        else:
            hora_atual = datetime.now().strftime("%H:%M")
            data_iso = data_atendimento.strftime("%Y-%m-%d")

            texto_servicos = " + ".join(servicos_selecionados) if servicos_selecionados else "Nenhum"
            lista_bebidas_txt = [f"{beb} ({qtd}x)" for beb, qtd in qtdes_bebidas.items()]
            texto_bebidas = " + ".join(lista_bebidas_txt) if lista_bebidas_txt else "Nenhuma"

            cursor.execute(
                """
                INSERT INTO lancamentos (
                    data, hora, cliente, servico, valor, valor_servicos, 
                    bebidas, valor_bebidas, valor_total, forma_pagamento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data_iso,
                    hora_atual,
                    cliente.strip(),
                    texto_servicos,
                    valor_final,
                    subtotal_servicos,
                    texto_bebidas,
                    subtotal_bebidas,
                    valor_final,
                    forma_pagamento,
                ),
            )
            conn.commit()
            st.success(f"Lançamento de **{cliente}** gravado com sucesso!")

# ==========================================
# ABA 2: FECHAMENTO DO DIA (Filtrado por Data)
# ==========================================
with aba2:
    st.subheader("Fechamento do Dia")

    data_consulta = st.date_input("Selecione a Data para Visualizar", datetime.today(), key="data_filtro")
    data_consulta_str = data_consulta.strftime("%Y-%m-%d")

    df = pd.read_sql_query(
        "SELECT hora AS Hora, cliente AS Cliente, servico AS Serviços, "
        "valor_servicos AS 'R$ Serviços', bebidas AS Bebidas, valor_bebidas AS 'R$ Bebidas', "
        "valor_total AS 'Total (R$)', forma_pagamento AS Pagamento "
        "FROM lancamentos WHERE data = ? ORDER BY id DESC",
        conn,
        params=(data_consulta_str,),
    )

    if not df.empty:
        tot_geral = df["Total (R$)"].sum()
        tot_servicos = df["R$ Serviços"].sum()
        tot_bebidas = df["R$ Bebidas"].sum()
        total_atendimentos = len(df)

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Faturamento Total", f"R$ {tot_geral:.2f}")
        m2.metric("✂️ Total Serviços", f"R$ {tot_servicos:.2f}")
        m3.metric("🍺 Total Bebidas", f"R$ {tot_bebidas:.2f}")

        st.divider()

        col_pag, col_det = st.columns(2)
        with col_pag:
            st.markdown("**Formas de Pagamento:**")
            por_pagamento = df.groupby("Pagamento")["Total (R$)"].sum().reset_index()
            for idx, row in por_pagamento.iterrows():
                st.write(f"• **{row['Pagamento']}**: R$ {row['Total (R$)']:.2f}")

        with col_det:
            st.markdown("**Resumo Geral:**")
            st.write(f"• Total de Clientes: **{total_atendimentos}**")
            st.write(
                f"• Participação de Bebidas: **{((tot_bebidas/tot_geral)*100 if tot_geral > 0 else 0):.1f}%**"
            )

        st.divider()

        st.markdown("**Histórico do Dia Selecionado:**")
        st.dataframe(
            df.style.format(
                {
                    "R$ Serviços": "R$ {:.2f}",
                    "R$ Bebidas": "R$ {:.2f}",
                    "Total (R$)": "R$ {:.2f}",
                }
            ),
            use_container_width=True,
        )
    else:
        st.info(f"Nenhum lançamento registrado no dia {data_consulta.strftime('%d/%m/%Y')}. O dia está limpo!")

# ==========================================
# ABA 3: CADASTRO DE SERVIÇOS E BEBIDAS
# ==========================================
with aba3:
    tab_s, tab_b = st.tabs(["✂️ Serviços", "🍺 Bebidas"])

    with tab_s:
        st.subheader("Novo Serviço")
        with st.form("form_novo_servico", clear_on_submit=True):
            n_serv = st.text_input("Nome do Serviço")
            p_serv = st.number_input("Preço (R$)", min_value=0.0, value=30.0, step=5.0)
            if st.form_submit_button("➕ Cadastrar Serviço"):
                if n_serv.strip():
                    try:
                        cursor.execute(
                            "INSERT INTO servicos (nome, preco_padrao) VALUES (?, ?)",
                            (n_serv.strip(), p_serv),
                        )
                        conn.commit()
                        st.success("Serviço adicionado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Serviço já existente.")

        st.divider()
        st.subheader("Editar Serviços")
        df_serv = pd.read_sql_query("SELECT id, nome AS Serviço, preco_padrao AS 'Preço (R$)' FROM servicos", conn)
        df_serv_edit = st.data_editor(df_serv, disabled=["id"], key="ed_serv")
        if st.button("💾 Salvar Alterações nos Serviços"):
            for _, r in df_serv_edit.iterrows():
                cursor.execute(
                    "UPDATE servicos SET nome=?, preco_padrao=? WHERE id=?",
                    (r["Serviço"], r["Preço (R$)"], r["id"]),
                )
            conn.commit()
            st.success("Atualizado com sucesso!")
            st.rerun()

    with tab_b:
        st.subheader("Nova Bebida / Produto")
        with st.form("form_nova_bebida", clear_on_submit=True):
            n_beb = st.text_input("Nome da Bebida")
            p_beb = st.number_input("Preço (R$)", min_value=0.0, value=10.0, step=1.0)
            if st.form_submit_button("➕ Cadastrar Bebida"):
                if n_beb.strip():
                    try:
                        cursor.execute(
                            "INSERT INTO bebidas (nome, preco_padrao) VALUES (?, ?)",
                            (n_beb.strip(), p_beb),
                        )
                        conn.commit()
                        st.success("Bebida adicionada!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bebida já existente.")

        st.divider()
        st.subheader("Editar Bebidas")
        df_beb = pd.read_sql_query("SELECT id, nome AS Bebida, preco_padrao AS 'Preço (R$)' FROM bebidas", conn)
        df_beb_edit = st.data_editor(df_beb, disabled=["id"], key="ed_beb")
        if st.button("💾 Salvar Alterações nas Bebidas"):
            for _, r in df_beb_edit.iterrows():
                cursor.execute(
                    "UPDATE bebidas SET nome=?, preco_padrao=? WHERE id=?",
                    (r["Bebida"], r["Preço (R$)"], r["id"]),
                )
            conn.commit()
            st.success("Atualizado com sucesso!")
            st.rerun()