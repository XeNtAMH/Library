import { useEffect, useEffectEvent, useMemo, useState } from 'react'
import './App.css'

const API = 'http://127.0.0.1:8000/api'
const samples = [
  { id: 1, title: 'La casa de los espíritus', author: 'Isabel Allende', genres: ['Novela', 'Realismo mágico'], cover_url: 'https://covers.openlibrary.org/b/isbn/9780553383805-L.jpg', physical_stock: 4, is_virtual: true, rental_price: '8.00' },
  { id: 2, title: 'Cien años de soledad', author: 'Gabriel García Márquez', genres: ['Novela', 'Clásico'], cover_url: 'https://covers.openlibrary.org/b/isbn/9788437604947-L.jpg', physical_stock: 2, is_virtual: true, rental_price: '7.00' },
  { id: 3, title: 'El infinito en un junco', author: 'Irene Vallejo', genres: ['Ensayo', 'Historia'], cover_url: 'https://covers.openlibrary.org/b/id/9689877-L.jpg', physical_stock: 0, is_virtual: true, rental_price: '9.00' },
  { id: 4, title: 'Nuestra parte de noche', author: 'Mariana Enríquez', genres: ['Terror', 'Novela'], cover_url: 'https://covers.openlibrary.org/b/id/10239068-L.jpg', physical_stock: 3, is_virtual: false, rental_price: '10.00' },
]
const roleName = { admin: 'Administrador', librarian: 'Bibliotecario', member: 'Lector' }

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('biblioteca-token') || '')
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('biblioteca-user') || 'null'))
  const [books, setBooks] = useState(samples)
  const [loans, setLoans] = useState([])
  const [requests, setRequests] = useState([])
  const [members, setMembers] = useState([])
  const [operations, setOperations] = useState([])
  const [tab, setTab] = useState('catalog')
  const [query, setQuery] = useState('')
  const [genre, setGenre] = useState('Todos')
  const [modal, setModal] = useState('')
  const [editingBook, setEditingBook] = useState(null)
  const [notice, setNotice] = useState('')
  const [online, setOnline] = useState(false)
  const staff = ['admin', 'librarian'].includes(user?.role)

  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Token ${token}` } : {}) },
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || Object.values(data).flat().join(' ') || 'No se pudo completar la acción.')
    return data
  }

  async function refresh() {
    try {
      const result = await api('/books/')
      setBooks(result.results || result)
      setOnline(true)
      if (!token) return
      const [profile, loanData, requestData] = await Promise.all([
        api('/auth/me/'), api('/loans/'), api('/virtual-requests/'),
      ])
      setUser((current) => ({ ...current, ...profile }))
      setLoans(loanData.results || loanData)
      setRequests(requestData.results || requestData)
      if (['admin', 'librarian'].includes(profile.role)) {
        const [memberData, operationData] = await Promise.all([api('/members/'), api('/inventory/')])
        setMembers(memberData.results || memberData)
        setOperations(operationData.results || operationData)
      }
    } catch { setOnline(false) }
  }

  const syncLibrary = useEffectEvent(refresh)
  useEffect(() => {
    const timer = setTimeout(() => syncLibrary(), 0)
    return () => clearTimeout(timer)
  }, [token])
  useEffect(() => {
    if (!modal) return undefined
    const previousOverflow = document.body.style.overflow
    const previousPaddingRight = document.body.style.paddingRight
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
    document.body.style.overflow = 'hidden'
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`
    return () => {
      document.body.style.overflow = previousOverflow
      document.body.style.paddingRight = previousPaddingRight
    }
  }, [modal])
  useEffect(() => {
    if (!notice) return undefined
    const timer = setTimeout(() => setNotice(''), 3500)
    return () => clearTimeout(timer)
  }, [notice])

  const genres = useMemo(() => ['Todos', ...new Set(books.flatMap((book) => book.genres || []))], [books])
  const visibleBooks = books.filter((book) => (book.physical_stock > 0 || book.is_virtual) &&
    `${book.title} ${book.author}`.toLowerCase().includes(query.toLowerCase()) &&
    (genre === 'Todos' || (book.genres || []).includes(genre)))

  async function submitAuth(event) {
    event.preventDefault()
    const signup = modal === 'signup'
    try {
      const data = await api(`/auth/${signup ? 'signup' : 'login'}/`, {
        method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))),
      })
      localStorage.setItem('biblioteca-token', data.token)
      localStorage.setItem('biblioteca-user', JSON.stringify(data.user))
      setToken(data.token)
      setUser(data.user)
      setModal('')
      setTab('catalog')
      setQuery('')
      setGenre('Todos')
    } catch (error) { setNotice(error.message) }
  }

  function logout() {
    localStorage.removeItem('biblioteca-token')
    localStorage.removeItem('biblioteca-user')
    setToken('')
    setUser(null)
    setTab('catalog')
  }

  async function act(path, payload, success, method = 'POST') {
    try {
      await api(path, { method, body: JSON.stringify(payload) })
      setNotice(success)
      await refresh()
      return true
    } catch (error) { setNotice(error.message) }
    return false
  }

  async function saveBook(event) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    data.physical_stock = Number(data.physical_stock)
    data.genres = data.genres.split(',').map((value) => value.trim()).filter(Boolean)
    data.is_virtual = data.is_virtual === 'on'
    const saved = await act(editingBook ? `/books/${editingBook.id}/` : '/books/', data, editingBook ? 'Libro actualizado.' : 'Título añadido.', editingBook ? 'PATCH' : 'POST')
    if (saved) {
      setModal('')
      setEditingBook(null)
    }
  }

  async function deleteBook(book) {
    if (!confirm(`¿Eliminar “${book.title}” del catálogo?`)) return
    const deleted = await act(`/books/${book.id}/`, {}, 'Libro eliminado.', 'DELETE')
    if (!deleted) setNotice('No se pudo eliminar. Puede estar asociado a alquileres o movimientos de inventario.')
  }

  function openBookForm(book = null) {
    setEditingBook(book)
    setModal('book')
  }

  async function saveOperation(event) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    data.quantity = Number(data.quantity)
    data.unit_price = Number(data.unit_price)
    await act('/inventory/', data, 'Operación de inventario registrada.')
    setModal('')
  }

  async function suspend(member) {
    if (member.is_banned) {
      await act(`/members/${member.id}/unban/`, {}, 'Suspensión levantada.')
      return
    }
    const reason = prompt(`Motivo de suspensión para ${member.first_name}:`)
    if (reason !== null) await act(`/members/${member.id}/ban/`, { reason }, 'Cuenta suspendida.')
  }

  const bookCard = (book) => <article className="book-card" key={book.id}>
    <div className="cover-wrap">
      <img src={book.cover_url || samples[0].cover_url} alt={`Portada de ${book.title}`} onError={(event) => { event.currentTarget.src = samples[0].cover_url }} />
      <span className="stock-tag">{book.physical_stock ? `${book.physical_stock} disponibles` : 'Solo digital'}</span>
    </div>
    <div className="book-meta">
      <small>{(book.genres || []).join(' · ')}</small>
      <h3>{book.title}</h3><p>{book.author}</p>
      <div className="book-actions"><span>{book.physical_stock > 0 ? `Alquiler Bs ${book.rental_price || '0.00'}` : 'Edición digital disponible'}</span>
        {book.physical_stock > 0 && <button title="Solicitar alquiler" onClick={() => user ? act('/loans/', { book: book.id }, 'Solicitud enviada al bibliotecario para aprobación.') : setModal('login')}>↗</button>}
        {book.is_virtual && <button title="Solicitar edición digital" onClick={() => user ? act('/virtual-requests/', { book: book.id }, 'Solicitud digital enviada.') : setModal('login')}>↓</button>}
      </div>
    </div>
  </article>

  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="#inicio" onClick={() => setTab('catalog')}><b>B</b><span>EL BUEN VIAJE<small>BIBLIOTECA · SANTA CLARA</small></span></a>
      <nav><button onClick={() => setTab('catalog')}>Catálogo</button>{user && <button onClick={() => setTab('account')}>Mi cuenta</button>}{staff && <button onClick={() => setTab('management')}>Gestión</button>}</nav>
      <div className="account-actions"><span className={token && user && online ? 'online' : ''}>● {token && user ? (online ? 'EN LÍNEA' : 'SIN CONEXIÓN') : 'DESCONECTADO'}</span>{user ? <><button onClick={() => setTab('account')}>{user.first_name || user.username}</button><button onClick={logout}>Salir</button></> : <><button onClick={() => setModal('login')}>Ingresar</button><button className="primary" onClick={() => setModal('signup')}>Crear cuenta ↗</button></>}</div>
    </header>

    <main>
      {tab === 'catalog' && <>
        <section className="hero">
          <div><small>● UN LUGAR PARA CADA HISTORIA</small><h1>El próximo capítulo<br />empieza <em>aquí.</em></h1><p>Explora historias, ideas y mundos. Encuentra el libro que no sabías que estabas buscando.</p><a href="#catalogo">Explorar colección ↓</a></div>
          <div className="hero-art"><div className="sun" /><div className="stack"><div>La vida<br />secreta de<br />los árboles</div><div>Pequeñas<br />cosas bellas</div><div>Una historia<br />interminable</div></div><span>LECTURAS QUE<br />NOS ENCUENTRAN</span></div>
        </section>
        <section className="catalog" id="catalogo">
          <div className="section-heading"><div><small>LA COLECCIÓN</small><h2>Libros para <em>quedarse.</em></h2></div><span>{visibleBooks.length} TÍTULOS</span></div>
          <div className="catalog-tools"><input placeholder="Buscar título o autor" value={query} onChange={(event) => setQuery(event.target.value)} /><div>{genres.slice(0, 6).map((item) => <button className={genre === item ? 'selected' : ''} key={item} onClick={() => setGenre(item)}>{item}</button>)}</div></div>
          {visibleBooks.length ? <div className="book-grid">{visibleBooks.map(bookCard)}</div> : <p className="empty-catalog">Aún no hay libros disponibles para alquiler o descarga. El personal puede añadir títulos desde el panel de control.</p>}
        </section>
        <section className="membership"><div><small>TU PRÓXIMA GRAN LECTURA</small><h2>Una biblioteca.<br /><em>Infinitas posibilidades.</em></h2></div><button onClick={() => user ? setTab('account') : setModal('signup')}>Hazte miembro ↗</button></section>
      </>}

      {tab === 'account' && <section className="workspace"><small>ESPACIO PERSONAL</small><h1>Hola, <em>{user?.first_name || user?.username}.</em></h1><p>{roleName[user?.role] || 'Lector'} · CI {user?.national_id || 'Completar perfil'} · {user?.phone || 'Completar teléfono'}</p>{user?.is_banned && <p className="warning">Cuenta suspendida. Contacta con biblioteca.</p>}<div className="columns"><Panel title="Mis alquileres">{loans.length ? loans.map((loan) => <Row key={loan.id} title={loan.book_title} detail={`Vence ${loan.due_date}`} status={loan.status} />) : <p>Aún no tienes alquileres.</p>}</Panel><Panel title="Ediciones digitales">{requests.length ? requests.map((item) => <Row key={item.id} title={item.book_title} detail={item.status === 'approved' ? <a href={item.download_url}>Descargar edición ↗</a> : 'Solicitud enviada'} status={item.status} />) : <p>Aún no tienes solicitudes.</p>}</Panel></div></section>}

      {tab === 'management' && staff && <section className="workspace"><small>CENTRO DE OPERACIONES</small><h1>La biblioteca,<br /><em>en movimiento.</em></h1><button className="primary" onClick={() => setModal('book')}>＋ Añadir título</button><div className="stats"><div>CATÁLOGO<strong>{books.length}</strong></div><div>PRÉSTAMOS<strong>{loans.filter((loan) => loan.status === 'active').length}</strong></div><div>SOLICITUDES<strong>{requests.filter((item) => item.status === 'pending').length}</strong></div><div>MIEMBROS<strong>{members.length}</strong></div></div><div className="columns"><Panel title="Préstamos">{loans.map((loan) => <Row key={loan.id} title={loan.book_title} detail={loan.member_name} action={loan.status === 'active' && <button onClick={() => act(`/loans/${loan.id}/return/`, {}, 'Devolución registrada.')}>Devolver</button>} />)}</Panel><Panel title="Solicitudes digitales">{requests.map((item) => <Row key={item.id} title={item.book_title} detail={item.member_name} action={item.status === 'pending' && <><button onClick={() => act(`/virtual-requests/${item.id}/`, { status: 'approved' }, 'Solicitud aprobada.', 'PATCH')}>Aprobar</button><button onClick={() => act(`/virtual-requests/${item.id}/`, { status: 'rejected' }, 'Solicitud rechazada.', 'PATCH')}>Rechazar</button></>} />)}</Panel><Panel title="Miembros">{members.map((member) => <Row key={member.id} title={`${member.first_name} ${member.last_name}`} detail={`CI ${member.national_id || '—'} · ${roleName[member.role]}`} action={<>{user?.role === 'admin' && <select aria-label={`Rol de ${member.first_name}`} value={member.role} onChange={(event) => act(`/members/${member.id}/set_role/`, { role: event.target.value }, 'Rol actualizado.', 'PATCH')}><option value="member">Usuario</option><option value="librarian">Bibliotecario</option><option value="admin">Admin</option></select>}{member.role === 'member' && <button onClick={() => suspend(member)}>{member.is_banned ? 'Levantar suspensión' : 'Suspender'}</button>}</>} />)}</Panel><Panel title="Compras y ventas"><button onClick={() => setModal('purchase')}>＋ Compra</button> <button onClick={() => setModal('sale')}>− Venta</button>{operations.map((item) => <Row key={item.id} title={item.book_title} detail={`${item.kind} · ${item.quantity} ejemplares`} />)}</Panel></div></section>}
      {tab === 'management' && staff && <section className="workspace management-inventory"><Panel title="Catálogo y stock"><div className="inventory-heading"><span>TÍTULO / AUTOR</span><span>FÍSICOS</span><span>DIGITAL</span><span>ACCIONES</span></div>{books.map((book) => <div className="inventory-row" key={book.id}><div><b>{book.title}</b><small>{book.author} · {(book.genres || []).join(', ') || 'Sin género'}</small></div><strong>{book.physical_stock}</strong><span>{book.is_virtual ? 'Disponible' : 'No'}</span><div className="inventory-actions"><button onClick={() => openBookForm(book)}>Editar</button><button className="delete-button" onClick={() => deleteBook(book)}>Eliminar</button></div></div>)}</Panel></section>}
      {tab === 'management' && staff && <section className="workspace management-followup"><div className="columns"><Panel title="Alquileres por aprobar">{loans.filter((loan) => loan.status === 'pending').map((loan) => <Row key={loan.id} title={loan.book_title} detail={`${loan.member_name} · CI ${loan.member_national_id || '—'} · ${loan.member_phone || 'sin teléfono'}`} action={<div className="review-actions"><button aria-label="Aprobar alquiler" onClick={() => act(`/loans/${loan.id}/approve/`, {}, 'Alquiler aprobado; stock actualizado.')}>Aprobar</button><button aria-label="Rechazar alquiler" onClick={() => act(`/loans/${loan.id}/reject/`, {}, 'Solicitud de alquiler rechazada.')}>Rechazar</button></div>} />)}{!loans.some((loan) => loan.status === 'pending') && <p>No hay solicitudes de alquiler pendientes.</p>}</Panel><Panel title="Perfiles y actividad">{members.map((member) => { const memberLoans = loans.filter((loan) => loan.user === member.user_id); const memberRequests = requests.filter((request) => request.user === member.user_id); return <Row key={member.id} title={`${member.first_name} ${member.last_name} · ${roleName[member.role]}`} detail={`CI ${member.national_id || '—'} · Tel. ${member.phone || '—'} · ${memberLoans.length} alquileres · ${memberRequests.length} solicitudes digitales`} status={member.is_banned ? 'Suspendido' : undefined} /> })}</Panel></div></section>}
    </main>

    <footer><a className="brand" href="#inicio"><b>B</b><span>EL BUEN VIAJE<small>BIBLIOTECA</small></span></a><span>SANTA CLARA · VILLA CLARA · CUBA</span><span>CONTACTO: 42 219761</span></footer>
    {notice && <div className="toast" role="status">{notice}<button onClick={() => setNotice('')}>×</button></div>}
    {modal && <div className="backdrop" onClick={(event) => event.target === event.currentTarget && setModal('')}><section className="modal"><button className="close" onClick={() => setModal('')}>×</button>
      {(modal === 'login' || modal === 'signup') && <><small>EL BUEN VIAJE · BIBLIOTECA</small><h2>{modal === 'signup' ? 'Una historia nueva.' : 'Qué bueno verte.'}</h2><form onSubmit={submitAuth}>{modal === 'signup' && <><label>Nombre<input name="first_name" required /></label><label>Apellidos<input name="last_name" required /></label><label>CI<input name="national_id" required /></label><label>Teléfono<input name="phone" required /></label><label>Correo<input type="email" name="email" /></label></>}<label>Usuario<input name="username" required /></label><label>Contraseña<input type="password" name="password" minLength="8" required /></label><button className="primary">{modal === 'signup' ? 'Crear cuenta' : 'Ingresar'} ↗</button></form><button onClick={() => setModal(modal === 'signup' ? 'login' : 'signup')}>{modal === 'signup' ? 'Ingresar' : 'Crear cuenta'}</button></>}
      {modal === 'book' && <><small>GESTIÓN DE COLECCIÓN</small><h2>{editingBook ? 'Editar título.' : 'Añadir un título.'}</h2><form onSubmit={saveBook}><label>Nombre<input name="title" required defaultValue={editingBook?.title || ''} /></label><label>Autor<input name="author" required defaultValue={editingBook?.author || ''} /></label><label>Géneros<input name="genres" placeholder="Novela, Historia" defaultValue={editingBook?.genres?.join(', ') || ''} /></label><label>Foto de portada (URL)<input name="cover_url" type="url" defaultValue={editingBook?.cover_url || ''} /></label><label>Ejemplares físicos<input name="physical_stock" type="number" min="0" defaultValue={editingBook?.physical_stock ?? 1} /></label><label>Precio alquiler<input name="rental_price" type="number" step="0.01" defaultValue={editingBook?.rental_price ?? '0'} /></label><label><input name="is_virtual" type="checkbox" defaultChecked={editingBook?.is_virtual || false} /> Edición digital disponible</label><label>URL edición digital<input name="virtual_url" type="url" defaultValue={editingBook?.virtual_url || ''} /></label><button className="primary">{editingBook ? 'Guardar cambios' : 'Guardar título'}</button></form></>}
      {(modal === 'purchase' || modal === 'sale') && <><small>CONTROL DE INVENTARIO</small><h2>Registrar {modal === 'purchase' ? 'compra' : 'venta'}.</h2><form onSubmit={saveOperation}><input type="hidden" name="kind" value={modal} /><label>Título<select name="book">{books.map((book) => <option value={book.id} key={book.id}>{book.title}</option>)}</select></label><label>Cantidad<input name="quantity" type="number" min="1" required /></label><label>Precio unitario<input name="unit_price" type="number" step="0.01" min="0" required /></label><button className="primary">Confirmar operación</button></form></>}
    </section></div>}
  </div>
}

function Panel({ title, children }) { return <section className="panel"><h2>{title}</h2>{children}</section> }
function Row({ title, detail, status, action }) { const labels = { pending: 'Pendiente', active: 'En curso', returned: 'Devuelto', rejected: 'Rechazado', approved: 'Aprobada' }; return <div className="row"><div><b>{title}</b><small>{detail}</small></div>{action || (status && <span className={`status ${status}`}>{labels[status] || status}</span>)}</div> }

export default App
