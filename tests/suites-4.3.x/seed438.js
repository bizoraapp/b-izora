async()=>{window.toast=()=>{};const T=todayStr(),P='2026-06-10';
 const close=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
 S.setObj('settings',{...S.obj('settings'),businessName:'Boutique Restore',currency:'FCFA',setupDone:true});
 [['pA','Rice 25kg',18000,15000,40],['pB','Phone',30000,25000,12],['pC','Soap',500,300,200]].forEach(([id,name,price,cost,stock],i)=>S.add('products',{id,sku:'SKU-00000'+(i+1),name,category:'Gen',cost,price,stock,unit:'pcs',tax:0,status:'active',added:P}));
 [['k1','Amina Ngo',0],['k2','Bello Tchami',50000],['k3','Chidi Eko',0]].forEach(([id,name,limit],i)=>S.add('customers',{id,name,phone:'+237 67000000'+i,limit,status:'active',added:P}));
 // POS cash sales (cash + MoMo), POS credit sale via real checkout
 const pos=(pid,m,recv)=>{close();go('pos');resetPosForm();addPosItemFromProduct(pid);document.getElementById('posMethod').value=m;document.getElementById('posReceived').value=String(recv);calcPosTotals();document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();close();};
 pos('pA','cash',20000);pos('pC','mobile-money',500);pos('pC','card',500);
 close();go('pos');resetPosForm();addPosItemFromProduct('pB');document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='k1';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();calcPosTotals();
 const dm=document.getElementById('posDepositMethod');if(dm){document.getElementById('posDeposit').value='0';}
 document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();close();
 // 4.3.8: POS credit deposit paid by Mobile Money and an invoice deposit by bank transfer (new selectors)
 if(typeof syncDepositMethod==='function'){
   close();go('pos');resetPosForm();addPosItemFromProduct('pB');document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='k2';document.getElementById('posDueDate').value=todayStr();calcPosTotals();
   document.getElementById('posDeposit').value='5000';syncDepositMethod('pos');document.getElementById('posDepositMethod').value='mobile-money';document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();close();
   close();openModal('mAddSale');resetSaleForm();const sc=document.getElementById('sCustomer');if(![...sc.options].some(o=>o.value==='k1'))sc.add(new Option('k1','k1'));sc.value='k1';document.getElementById('itemsBody').innerHTML='';addItemRow('Service',1,8000);calcInvTotal();
   document.getElementById('sInitPay').value='3000';syncDepositMethod('inv');document.getElementById('sDepositMethod').value='bank-transfer';document.getElementById('saveSaleBtn').disabled=false;saveSale();close();
 }
 // invoices + payments of every method through Record Payment
 S.add('sales',{id:'iv1',cid:'k2',amount:60000,date:P,due:P,items:[{name:'Goods',qty:1,price:60000,subtotal:60000}],status:'pending',docNum:'INV-IV1'});
 S.add('sales',{id:'iv2',cid:'k3',amount:40000,date:P,due:P,items:[{name:'Goods',qty:1,price:40000,subtotal:40000}],status:'pending',docNum:'INV-IV2'});
 const pay=(cid,inv,amt,m)=>{close();openModal('mAddPay');resetPayForm();const c=document.getElementById('pCustomer');if(![...c.options].some(o=>o.value===cid))c.add(new Option(cid,cid));c.value=cid;const s=document.getElementById('pInvoice');if(![...s.options].some(o=>o.value===inv))s.add(new Option(inv,inv));s.value=inv;document.getElementById('pAmount').value=String(amt);document.getElementById('pMethod').value=m;savePay();close();};
 pay('k2','iv1',5000,'cash');pay('k2','iv1',5000,'mobile-money');pay('k2','iv1',5000,'bank-transfer');pay('k2','iv1',5000,'card');pay('k2','iv1',5000,'cheque');pay('k2','iv1',5000,'other');
 // overpayment (Owner / AC off -> confirm) on iv2: 45,000 cash -> 5,000 credit (method cash)
 pay('k3','iv2',45000,'cash');document.getElementById('mConfirmBtn').click();close();
 // apply part of credit to another invoice (account credit payment)
 S.add('sales',{id:'iv3',cid:'k3',amount:2000,date:P,due:P,items:[{name:'Goods',qty:1,price:2000,subtotal:2000}],status:'pending',docNum:'INV-IV3'});
 promptApplyCredit('k3');document.getElementById('mConfirmBtn').click();close();
 // refunds (cash + mobile money)
 refundAccountCredit('k3',1000,'cash');refundAccountCredit('k3',1000,'mobile-money');
 // expenses with different methods
 const exp=(amt,m)=>{close();openAddExpense();document.getElementById('expAmount').value=String(amt);document.getElementById('expPayMethod').value=m;saveExpense();close();};
 exp(3000,'cash');exp(2500,'mobile-money');exp(1500,'bank-transfer');
 // legacy records: historical payment without method, non-standard spelling
 S.add('payments',{id:'legacy1',invId:'iv1',cid:'k2',amount:1000,date:P,ref:'',notes:'old record'});
 S.add('payments',{id:'legacy2',invId:'iv1',cid:'k2',amount:1000,date:P,method:'mobile money',ref:'',notes:'old spelling'});
 // drawer
 close();go('inventory');const o=document.getElementById('cdOpening');o.value='15000';saveCashDrawer();commitCashDrawerEdit();
 const c=document.getElementById('cdClosing');c.value='40000';saveCashDrawer();commitCashDrawerEdit();
 await new Promise(r=>setTimeout(r,500));return true}
