/**
 * White Script templates por nicho + idioma (PT-BR / EN / ES).
 * Estilo cardápio do mercado: nichos de ads + script safe/editável.
 */
(() => {
  const LANGS = [
    { id: "pt", label: "Português", short: "PT-BR", flag: "🇧🇷" },
    { id: "en", label: "English", short: "EN", flag: "🇺🇸" },
    { id: "es", label: "Español", short: "ES", flag: "🇪🇸" },
  ];

  /** @param {{pt:string,en:string,es:string}} o */
  const t = (o) => o;

  const N = [
    {
      id: "mmo",
      icon: "$",
      label: "Ganhar Dinheiro / MMO",
      copies: [
        {
          id: "mmo_1",
          title: t({
            pt: "Oportunidade online",
            en: "Online opportunity",
            es: "Oportunidad online",
          }),
          text: t({
            pt:
              "Existem formas legítimas de gerar renda pela internet com dedicação e método. " +
              "Resultados variam conforme esforço, mercado e constância. " +
              "Pesquise, estude e confira termos oficiais antes de investir tempo ou dinheiro. " +
              "Nenhuma renda é garantida. Faça suas próprias escolhas com responsabilidade.",
            en:
              "There are legitimate ways to earn online with dedication and a clear method. " +
              "Results vary with effort, market conditions, and consistency. " +
              "Research, learn, and read official terms before investing time or money. " +
              "No income is guaranteed. Make your own informed decisions.",
            es:
              "Hay formas legítimas de generar ingresos en internet con dedicación y método. " +
              "Los resultados varían según el esfuerzo, el mercado y la constancia. " +
              "Investiga, estudia y revisa los términos oficiales antes de invertir tiempo o dinero. " +
              "Ningún ingreso está garantizado. Decide con responsabilidad.",
          }),
        },
        {
          id: "mmo_2",
          title: t({
            pt: "Trabalho e método",
            en: "Work and method",
            es: "Trabajo y método",
          }),
          text: t({
            pt:
              "Ganhar dinheiro online exige aprendizado, disciplina e paciência. " +
              "Evite promessas milagrosas e avalie riscos com calma. " +
              "Use ferramentas legais, cumpra as regras da plataforma e foque em valor real para o cliente. " +
              "Consulte fontes confiáveis e siga apenas o que fizer sentido para você.",
            en:
              "Making money online takes learning, discipline, and patience. " +
              "Avoid miracle promises and assess risks carefully. " +
              "Use legal tools, follow platform rules, and focus on real value for customers. " +
              "Check trusted sources and only follow what makes sense for you.",
            es:
              "Ganar dinero en línea requiere aprendizaje, disciplina y paciencia. " +
              "Evita promesas milagrosas y evalúa los riesgos con calma. " +
              "Usa herramientas legales, cumple las reglas de la plataforma y ofrece valor real. " +
              "Consulta fuentes confiables y sigue solo lo que tenga sentido para ti.",
          }),
        },
      ],
    },
    {
      id: "riqueza",
      icon: "↗",
      label: "Riqueza / Prosperidade",
      copies: [
        {
          id: "riq_1",
          title: t({
            pt: "Educação financeira",
            en: "Financial education",
            es: "Educación financiera",
          }),
          text: t({
            pt:
              "Prosperidade começa com hábitos: orçamento, reserva de emergência e decisões conscientes. " +
              "Este conteúdo é educativo e não é recomendação de investimento. " +
              "Todo investimento envolve risco, inclusive perda de capital. " +
              "Informe-se em fontes oficiais e, se precisar, fale com um profissional habilitado.",
            en:
              "Prosperity starts with habits: budgeting, an emergency fund, and conscious decisions. " +
              "This content is educational and is not investment advice. " +
              "All investing involves risk, including loss of capital. " +
              "Use official sources and consult a qualified professional if needed.",
            es:
              "La prosperidad empieza con hábitos: presupuesto, fondo de emergencia y decisiones conscientes. " +
              "Este contenido es educativo y no es recomendación de inversión. " +
              "Toda inversión implica riesgo, incluida la pérdida de capital. " +
              "Infórmate en fuentes oficiales y consulta a un profesional si lo necesitas.",
          }),
        },
        {
          id: "riq_2",
          title: t({
            pt: "Decisões com calma",
            en: "Calm decisions",
            es: "Decisiones con calma",
          }),
          text: t({
            pt:
              "Construir patrimônio leva tempo. Evite atalhos e pressão de urgência. " +
              "Compare opções, entenda taxas e prazos, e só avance se estiver confortável. " +
              "Não há garantia de retorno. Sua realidade financeira é única.",
            en:
              "Building wealth takes time. Avoid shortcuts and false urgency. " +
              "Compare options, understand fees and timelines, and only proceed if you are comfortable. " +
              "Returns are not guaranteed. Your financial situation is unique.",
            es:
              "Construir patrimonio lleva tiempo. Evita atajos y urgencias artificiales. " +
              "Compara opciones, entiende comisiones y plazos, y avanza solo si te sientes cómodo. " +
              "No hay garantía de retorno. Tu realidad financiera es única.",
          }),
        },
      ],
    },
    {
      id: "peso",
      icon: "⚖",
      label: "Perda de Peso",
      copies: [
        {
          id: "peso_1",
          title: t({
            pt: "Hábitos saudáveis",
            en: "Healthy habits",
            es: "Hábitos saludables",
          }),
          text: t({
            pt:
              "Emagrecimento sustentável combina alimentação equilibrada, movimento e sono. " +
              "Resultados variam de pessoa para pessoa. Não há fórmula mágica. " +
              "Consulte um médico ou nutricionista antes de mudanças intensas. " +
              "Este conteúdo é informativo e não substitui orientação profissional.",
            en:
              "Sustainable weight loss combines balanced eating, movement, and sleep. " +
              "Results vary by person. There is no magic formula. " +
              "See a doctor or dietitian before major changes. " +
              "This content is informational and does not replace professional advice.",
            es:
              "La pérdida de peso sostenible combina alimentación equilibrada, movimiento y sueño. " +
              "Los resultados varían según cada persona. No hay fórmula mágica. " +
              "Consulta a un médico o nutricionista antes de cambios intensos. " +
              "Este contenido es informativo y no sustituye orientación profesional.",
          }),
        },
        {
          id: "peso_2",
          title: t({
            pt: "Constância sem milagre",
            en: "Consistency, not miracles",
            es: "Constancia, no milagros",
          }),
          text: t({
            pt:
              "Metas realistas e constância costumam superar dietas extremas. " +
              "Hidrate-se, respeite o corpo e evite promessas irreais. " +
              "Em caso de condição de saúde, busque avaliação presencial.",
            en:
              "Realistic goals and consistency usually beat extreme diets. " +
              "Stay hydrated, respect your body, and avoid unrealistic promises. " +
              "If you have a health condition, seek in-person evaluation.",
            es:
              "Metas realistas y constancia suelen superar dietas extremas. " +
              "Hidrátate, respeta tu cuerpo y evita promesas irreales. " +
              "Si tienes una condición de salud, busca evaluación presencial.",
          }),
        },
      ],
    },
    {
      id: "diabetes",
      icon: "💊",
      label: "Diabetes",
      copies: [
        {
          id: "dia_1",
          title: t({
            pt: "Cuidado com orientação",
            en: "Care with guidance",
            es: "Cuidado con orientación",
          }),
          text: t({
            pt:
              "Diabetes exige acompanhamento médico individualizado. " +
              "Este material é apenas informativo e não substitui consulta, exame ou prescrição. " +
              "Não altere medicação por conta própria. " +
              "Fale com seu médico ou equipe de saúde para orientações adequadas ao seu caso.",
            en:
              "Diabetes requires individualized medical care. " +
              "This material is informational only and does not replace consultation, tests, or prescriptions. " +
              "Do not change medication on your own. " +
              "Talk to your doctor or care team for guidance specific to your case.",
            es:
              "La diabetes requiere seguimiento médico individualizado. " +
              "Este material es solo informativo y no sustituye consulta, exámenes o prescripción. " +
              "No cambies la medicación por tu cuenta. " +
              "Habla con tu médico o equipo de salud para orientación adecuada a tu caso.",
          }),
        },
        {
          id: "dia_2",
          title: t({
            pt: "Rotina e hábitos",
            en: "Routine and habits",
            es: "Rutina y hábitos",
          }),
          text: t({
            pt:
              "Alimentação, atividade física e monitoramento fazem parte do cuidado diário. " +
              "Cada organismo responde de forma diferente. " +
              "Busque fontes confiáveis e profissionais habilitados. Não há cura milagrosa neste conteúdo.",
            en:
              "Nutrition, activity, and monitoring are part of daily care. " +
              "Every body responds differently. " +
              "Use trusted sources and qualified professionals. This content does not offer a miracle cure.",
            es:
              "Alimentación, actividad física y monitoreo forman parte del cuidado diario. " +
              "Cada organismo responde de forma distinta. " +
              "Busca fuentes confiables y profesionales habilitados. Este contenido no ofrece cura milagrosa.",
          }),
        },
      ],
    },
    {
      id: "de",
      icon: "♥",
      label: "Disfunção Erétil (DE)",
      copies: [
        {
          id: "de_1",
          title: t({
            pt: "Saúde com privacidade",
            en: "Health with privacy",
            es: "Salud con privacidad",
          }),
          text: t({
            pt:
              "Questões de saúde sexual merecem avaliação profissional e privacidade. " +
              "Este conteúdo é informativo e não diagnostica nem trata condições. " +
              "Consulte um médico antes de qualquer suplemento, medicamento ou tratamento. " +
              "Evite automedicação e promessas irreais.",
            en:
              "Sexual health topics deserve professional care and privacy. " +
              "This content is informational and does not diagnose or treat conditions. " +
              "See a doctor before any supplement, medicine, or treatment. " +
              "Avoid self-medication and unrealistic promises.",
            es:
              "Los temas de salud sexual merecen evaluación profesional y privacidad. " +
              "Este contenido es informativo y no diagnostica ni trata condiciones. " +
              "Consulta a un médico antes de cualquier suplemento, medicamento o tratamiento. " +
              "Evita la automedicación y las promesas irreales.",
          }),
        },
        {
          id: "de_2",
          title: t({
            pt: "Orientação médica",
            en: "Medical guidance",
            es: "Orientación médica",
          }),
          text: t({
            pt:
              "Fatores físicos e emocionais podem influenciar a função sexual. " +
              "Só um profissional pode avaliar o seu caso. " +
              "Informações gerais não substituem consulta. Cuide da saúde de forma responsável.",
            en:
              "Physical and emotional factors can influence sexual function. " +
              "Only a professional can assess your case. " +
              "General information does not replace a consultation. Care for your health responsibly.",
            es:
              "Factores físicos y emocionales pueden influir en la función sexual. " +
              "Solo un profesional puede evaluar tu caso. " +
              "La información general no sustituye una consulta. Cuida tu salud con responsabilidad.",
          }),
        },
      ],
    },
    {
      id: "memoria",
      icon: "🧠",
      label: "Perda de Memória / Saúde Cerebral",
      copies: [
        {
          id: "mem_1",
          title: t({
            pt: "Cérebro e hábitos",
            en: "Brain and habits",
            es: "Cerebro y hábitos",
          }),
          text: t({
            pt:
              "Sono, movimento, socialização e aprendizado contínuo apoiam a saúde cerebral. " +
              "Este conteúdo é educativo e não substitui avaliação médica. " +
              "Esquecimentos frequentes merecem investigação profissional. " +
              "Não há garantia de melhora com qualquer produto ou rotina genérica.",
            en:
              "Sleep, movement, social connection, and continuous learning support brain health. " +
              "This content is educational and does not replace medical evaluation. " +
              "Frequent forgetfulness deserves professional investigation. " +
              "No generic product or routine guarantees improvement.",
            es:
              "Sueño, movimiento, socialización y aprendizaje continuo apoyan la salud cerebral. " +
              "Este contenido es educativo y no sustituye evaluación médica. " +
              "Los olvidos frecuentes merecen investigación profesional. " +
              "Ningún producto o rutina genérica garantiza mejora.",
          }),
        },
        {
          id: "mem_2",
          title: t({
            pt: "Informação responsável",
            en: "Responsible information",
            es: "Información responsable",
          }),
          text: t({
            pt:
              "Suplementos e programas de foco devem ser avaliados com critério. " +
              "Leia rótulos, busque evidências e fale com um profissional de saúde. " +
              "Resultados individuais variam. Priorize segurança e acompanhamento.",
            en:
              "Supplements and focus programs should be evaluated carefully. " +
              "Read labels, look for evidence, and talk to a healthcare professional. " +
              "Individual results vary. Prioritize safety and follow-up care.",
            es:
              "Los suplementos y programas de enfoque deben evaluarse con criterio. " +
              "Lee etiquetas, busca evidencia y habla con un profesional de salud. " +
              "Los resultados individuales varían. Prioriza seguridad y seguimiento.",
          }),
        },
      ],
    },
    {
      id: "antiage",
      icon: "⏱",
      label: "Anti-Envelhecimento / Rejuvenescimento",
      copies: [
        {
          id: "age_1",
          title: t({
            pt: "Cuidados realistas",
            en: "Realistic care",
            es: "Cuidados realistas",
          }),
          text: t({
            pt:
              "Cuidar da pele e do bem-estar envolve rotina, proteção solar e hábitos saudáveis. " +
              "Resultados estéticos dependem de genética, idade e consistência. " +
              "Não há milagre. Em procedimentos, busque profissionais qualificados. " +
              "Leia instruções de uso e faça teste de sensibilidade quando indicado.",
            en:
              "Skin and wellness care involve routine, sun protection, and healthy habits. " +
              "Aesthetic results depend on genetics, age, and consistency. " +
              "There is no miracle. For procedures, seek qualified professionals. " +
              "Read usage instructions and patch-test when recommended.",
            es:
              "Cuidar de la piel y el bienestar implica rutina, protección solar y hábitos saludables. " +
              "Los resultados estéticos dependen de genética, edad y constancia. " +
              "No hay milagro. En procedimientos, busca profesionales calificados. " +
              "Lee instrucciones de uso y haz prueba de sensibilidad cuando corresponda.",
          }),
        },
        {
          id: "age_2",
          title: t({
            pt: "Expectativas honestas",
            en: "Honest expectations",
            es: "Expectativas honestas",
          }),
          text: t({
            pt:
              "Produtos e hábitos podem apoiar aparência e conforto, sem reverter a idade. " +
              "Consulte dermatologista em dúvidas ou reações. " +
              "Escolha com informação clara e sem pressão de urgência.",
            en:
              "Products and habits may support appearance and comfort without reversing age. " +
              "See a dermatologist for questions or reactions. " +
              "Choose with clear information and without false urgency.",
            es:
              "Productos y hábitos pueden apoyar la apariencia y el confort sin revertir la edad. " +
              "Consulta a un dermatólogo ante dudas o reacciones. " +
              "Elige con información clara y sin urgencia artificial.",
          }),
        },
      ],
    },
    {
      id: "geral",
      icon: "★",
      label: "Geral / E-commerce",
      copies: [
        {
          id: "geral_1",
          title: t({
            pt: "Oferta oficial",
            en: "Official offer",
            es: "Oferta oficial",
          }),
          text: t({
            pt:
              "Oferta especial por tempo limitado. Confira as condições oficiais no site. " +
              "Produto de qualidade com garantia e suporte ao cliente. " +
              "Aproveite pagamento e frete conforme o regulamento da loja.",
            en:
              "Special offer for a limited time. Check official terms on the website. " +
              "Quality product with warranty and customer support. " +
              "Payment and shipping follow the store policy.",
            es:
              "Oferta especial por tiempo limitado. Consulta las condiciones oficiales en el sitio. " +
              "Producto de calidad con garantía y soporte al cliente. " +
              "Pago y envío según el reglamento de la tienda.",
          }),
        },
      ],
    },
  ];

  function normLang(lang) {
    const l = String(lang || "pt").toLowerCase();
    if (l.startsWith("en")) return "en";
    if (l.startsWith("es") || l.startsWith("spa")) return "es";
    return "pt";
  }

  function pick(obj, lang) {
    if (!obj) return "";
    if (typeof obj === "string") return obj;
    const L = normLang(lang);
    return obj[L] || obj.pt || obj.en || obj.es || "";
  }

  window.GW_WHITE_PRESETS = {
    langs: LANGS,
    niches: N,
    defaultNiche: "mmo",
    defaultLang: "pt",
    normLang,
    pick,
    findNiche(id) {
      return N.find((n) => n.id === id) || N[0];
    },
    findCopy(nicheId, copyId) {
      const n = this.findNiche(nicheId);
      return (n.copies || []).find((c) => c.id === copyId) || (n.copies || [])[0];
    },
    getText(nicheId, copyId, lang) {
      const c = this.findCopy(nicheId, copyId);
      return pick(c && c.text, lang);
    },
    getTitle(nicheId, copyId, lang) {
      const c = this.findCopy(nicheId, copyId);
      return pick(c && c.title, lang);
    },
    defaultText(lang) {
      const n = this.findNiche(this.defaultNiche);
      const c = n.copies[0];
      return pick(c.text, lang || this.defaultLang);
    },
  };
})();
