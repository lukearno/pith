
customElements.define('x-input', class XInput extends HTMLElement {
  
  static formAssociated = true;
  formAssociatedCallback(form) {
    this.form = form;
  }
  constructor() {
    super();
    this.internals = this.attachInternals();
    this.setValue('');
  }
  setValue(v) {
    this.value = v;
    this.internals.setFormValue(v);
  }
  connectedCallback() {
    const root = this.attachShadow({ mode: 'closed' })
    const name = this.getAttribute("name");
    const placeholder = this.getAttribute("placeholder");
    const autofocus = this.getAttribute("autofocus");
    const x_type = this.getAttribute("x-type");
    let colspan;
    if (this.hasAttribute("short")) {
      colspan = "px-10 lg:px-2 lg:col-span-1";
    } else {
      colspan = "lg:col-span-3";
    }
    root.innerHTML = `
      <style>@import "/css/site.css";</style>
      <formset class="block grid grid-cols-1 lg:grid-cols-4">
        <label class="lg:col-span-1 hidden lg:inline text-left lg:text-right mr-3" 
               for="${name}"><slot>Slot</slot></label>
        <input class="${colspan} px-2
                      bg-black 
                      border-1 border-light rounded text-cyanLight"
               name="${name}" type="${x_type}" 
               placeholder="${placeholder}" required ${autofocus}
               >
        <slot name="more"></slot>
      </formset>
    `
    root.querySelector("input").addEventListener("change", e => {
      this.setValue(e.target.value);
    });
    htmx.process(root)
  }
  
})

customElements.define('cv-office', class CVOffice extends HTMLElement {

  connectedCallback() {
    const root = this.attachShadow({ mode: 'closed' })
    const office = this.getAttribute("office");
    const tenure = this.getAttribute("tenure");
    const note = this.getAttribute("note");
    root.innerHTML = `
      <style>@import "/css/site.css";</style>
      <div hx-on:click="me('.x-show-drawer', this).on('click').classToggle('hidden')
                        && me('.x-drawer', this).on('click').classToggle('hidden')
                       " class="pb-1">
        <div class="font-bold">
          <strong class="text-cyanLight">${office}</strong>
          <strong class="text-light">(${tenure})</strong>
          <strong class="text-orangeLight">[${note}]</strong>
        </div>
        <div class="bg-dark rounded mt-2 text-light font-bold px-2 py-1"><slot name="story">Story</slot></div>
        <div class="x-show-drawer text-small text-orangeLight py-2
                    transition-height ease-in-out duration-500
                    ">
          <slot name="story"><span class="italic px-2">click for more...</span></slot>
        </div>
        <div class="x-drawer hidden transition-height ease-in-out duration-500">
          <slot>Slot</slot>
        </div>
      </div>
    `
    htmx.process(root)
  }
  
})
