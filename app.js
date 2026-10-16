const io = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{
    if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
  });
},{threshold:.12, rootMargin:'0px 0px -8% 0px'});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));

// stagger card reveals
document.querySelectorAll('.card').forEach((c,i)=>{
  c.style.transitionDelay = (Math.min(i,8)*0.06)+'s';
});

// animate ledger bars after reveal
const bars = document.querySelectorAll('[data-bar]');
const barIo = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{
    if(e.isIntersecting){
      e.target.style.width = e.target.dataset.bar;
      barIo.unobserve(e.target);
    }
  });
},{threshold:.4});
bars.forEach(b=>barIo.observe(b));