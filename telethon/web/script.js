var choosingOrigin = false;

function newContact() {
    const li = document.createElement('li');
    li.innerHTML = '<input placeholder="API hash" type="text">\
    <input placeholder="API id" type="number">\
    <input placeholder="+55" type="text">';
    li.querySelectorAll("input").forEach(element => {
        element.value = ""
    })
    const ul = document.querySelector("ul.contacts")
    ul.appendChild(li);
    ul.scrollTop = ul.scrollHeight;
    return li
}

eel.expose(exibir)
function exibir(mensagem) {
    const p = document.createElement("p")
    p.innerText = mensagem
    const output = document.querySelector("div.output")
    output.appendChild(p)
    output.scrollTop = output.scrollHeight;
}
eel.expose(perguntar)
function perguntar(mensagem) { return prompt(mensagem) }

eel.expose(carregarContatos)
function carregarContatos(contatos) {
    let last = document.querySelector(
        ".contacts ul")
    last.innerHTML = '';
    contatos.forEach(contato => {
        last = newContact();
        const inputList = last.querySelectorAll("input");
        inputList[0].value = contato["hash"];
        inputList[1].value = contato["id"];
        inputList[2].value = contato["number"];
    })
}

function callListGroups(destino = false) {
    document.querySelectorAll(
        "section.config .chooses button"
    ).forEach(button => {
        button.disabled = true;
    })
    choosingOrigin = !destino;
    if (choosingOrigin) {
        document.querySelector(
            ".message button"
        ).disabled = true;
    }
    eel.listar_grupos(destino);
}

eel.expose(listGroups)
function listGroups(name, index) {
    document.querySelector(".groups").style.display = "flex";
    const li = document.createElement("li");
    li.innerText = name;
    li.setAttribute("key", index);
    li.addEventListener("click", () => {
        selectGroup(li);
    });
    document.querySelector(".groups ul").appendChild(li);
    scrollTo(0, 0)
}

function selectGroup(li) {
    document.querySelector(
        ".groups"
    ).style.display = "none";
    const index = li.getAttribute("key");
    const inputList = document.querySelectorAll(
        ".chooses input")
    document.querySelectorAll(
        "section.config .chooses button"
    ).forEach(button => {
        button.disabled = false;
    })
    if (choosingOrigin) {
        inputList[0].value = li.innerText;
        document.querySelector(
            ".message button"
        ).disabled = false;
    } else {
        inputList[1].value = li.innerText;
    }
    if (inputList[0].value !== "" && inputList[1].value !== "") {
        document.querySelector(
            "#start"
        ).style.display = "flex"
    }
    eel.escolher_grupo(index);
}

function changeConfig() {
    const pause = document.querySelector("input#pause").value;
    const skip = document.querySelector("input#skip").value;
    const online = document.querySelector("input#online").value;
    const limit = document.querySelector("input#limit").value;
    const message = document.querySelector("#message").value;
    eel.modificar_config({
        "pausar": pause, "limitar": limit,
        "offset": skip, "filtro": online,
        "mensagem": {"msg": message,
            "path": "", "audio": false}
    })
}

function connected() {
    document.querySelectorAll(
        "section.config .chooses button"
    ).forEach(button => {
        button.disabled = false;
    })
    document.querySelector(
        "button#connect"
    ).style.display = "none"
    document.querySelectorAll(
        ".contacts input"
    ).forEach(element => {
        element.disabled = true;
    })
    document.querySelector(
        ".contacts button"
    ).style.display = "none"
}

function conectar() {
    const lists = document.querySelectorAll(
        ".contacts ul li");
    const contacts = [];
    lists.forEach(list => {
        const inputList = list.querySelectorAll(
            "input")
        if (inputList[2].value !== "") {
            contacts.push({
                "id": inputList[1].value,
                "hash": inputList[0].value,
                "number": inputList[2].value
            });
        }
    })
    if (contacts.length > 0) {
        eel.conectar(contacts)(result => {
            if (result) {
                connected();
            } else {
                alert("Não conseguiu se conectar!")
            }
        })
    } else {
        alert("É necessário pelo menos uma conta do telegram na aba de contatos.")
    }
}
function start(modo) {
    document.querySelectorAll(
        "input"
    ).forEach(element => {
        element.disabled = true;
    })
    document.querySelectorAll(
        "button"
    ).forEach(element => {
        element.disabled = true;
    })
    document.querySelector(
        "textarea"
    ).disabled = true;
    eel.rodar_programa(modo);
}
function carregar() {
    eel.carregar_config()(config => {
        document.querySelector("input#pause").value  = config["pausar"] 
        document.querySelector("input#skip").value   = config["offset"] 
        document.querySelector("input#online").value = config["filtro"] 
        document.querySelector("input#limit").value = config["limitar"] 
    })
}

eel.expose(changeLicense)
function changeLicense(message) {
    if (message === "Renove a licença") {
        document.querySelector(
            "sup#license"
        ).innerHTML = `<button onclick = "eel.handle_login()"> 
            Logar </button>`;
        document.querySelector(
            "#connect"
        ).disabled = true;
    } else {
        document.querySelector(
            "sup#license"
        ).innerHTML = message
        document.querySelector(
            "#connect"
        ).disabled = false;
    }
}