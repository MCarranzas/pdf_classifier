delete 
from batches  
where user_id in (
select u.id
from users u where u.username not in ('mcarranza', 'gonchito','marito')
)

delete 
from documents  
where user_id in (
select u.id
from users u where u.username not in ('mcarranza', 'gonchito','marito')
)

delete 
from document_reviews 
where usuario_username not in  ('mcarranza', 'gonchito','marito')

delete from users where username not in ('mcarranza', 'gonchito','marito')