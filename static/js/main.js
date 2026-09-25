var menu = document.querySelector('#menu-bars');
var navbar = document.querySelector('.mobile-nav');
var mobile_hide = document.querySelector('#mobile-hide');

$("body").click(function(e) {
  if (!(e.target.class == "navbar") && !($(e.target).parents(".navbar").length)) {
    if (e.target != menu && navbar.classList.contains('active')) {
      // Check if the click happened outside the navbar
      mobile_navbar(); 
    }
  }
});
menu.onclick = () =>{mobile_navbar()}
mobile_hide.onclick = ()=>{mobile_navbar()}

function mobile_navbar(){
  var isOpen = navbar.classList.toggle('active');
  menu.classList.toggle('fa-bars', !isOpen);
  menu.classList.toggle('fa-times', isOpen);
  menu.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  menu.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
}

var swiper = new Swiper(".home-slider", {
    spaceBetween: 30,
    centeredSlides: true,
    autoplay: {
      delay: 7500,
      disableOnInteraction: false,
    },
    // pagination: {
    //   el: ".swiper-pagination",
    //   clickable: true,
    // },
    loop:true,
  });

  var swiper = new Swiper(".anime-slider", {
    slidesPerView: 'auto',
    spaceBetween: 30,
    centeredSlides: true,
    autoplay: {
      delay: 4500,
      disableOnInteraction: false,
    },
    // pagination: {
    //   el: ".swiper-slide",
    //   clickable: true,
    // },
    loop:true,
    breakpoints: {
      420: {
        slidesPerView: 1,
        spaceBetween: 10,
      },
      768: {
        slidesPerView: 2,
        spaceBetween: 20
      },
      1024: {
        slidesPerView: 3,
        spaceBetween: 25,
      },
      1450: {
        slidesPerView: 4,
        spaceBetween: 30,
      }
    }
  });