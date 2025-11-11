import type { Product, User, Conversation } from '../types'

export const PRODUCTS: Product[] = [
  {
    id: 'p1',
    title: 'Auriculares inalámbricos X1',
    description: 'Auriculares Bluetooth con cancelación de ruido, batería 30h y micrófono integrado.',
    price: 59.99,
    images: ['https://picsum.photos/seed/p1/800/600'],
    category: 'Electrónica',
    stock: 25,
    rating: 4.5
  },
  {
    id: 'p2',
    title: 'Smartwatch Active 2',
    description: 'Reloj inteligente con monitor de ritmo cardiaco, GPS y resistencia al agua 5ATM.',
    price: 129.99,
    images: ['https://picsum.photos/seed/p2/800/600'],
    category: 'Wearables',
    stock: 12,
    rating: 4.2
  },
  {
    id: 'p3',
    title: 'Cafetera Espresso Compact',
    description: 'Cafetera espresso compacta, 15 bares, depósito desmontable y función vapor.',
    price: 89.5,
    images: ['https://picsum.photos/seed/p3/800/600'],
    category: 'Hogar',
    stock: 8,
    rating: 4.6
  },
  {
    id: 'p4',
    title: 'Mochila urbana 20L',
    description: 'Mochila resistente al agua, múltiples compartimentos y puerto USB.',
    price: 39.0,
    images: ['https://picsum.photos/seed/p4/800/600'],
    category: 'Accesorios',
    stock: 40,
    rating: 4.1
  },
  {
    id: 'p5',
    title: 'Silla ergonómica OfficePro',
    description: 'Silla con soporte lumbar, ajustes de altura y reposabrazos 4D.',
    price: 199.99,
    images: ['https://picsum.photos/seed/p5/800/600'],
    category: 'Muebles',
    stock: 5,
    rating: 4.7
  },
  {
    id: 'p6',
    title: 'Teclado mecánico K-100',
    description: 'Teclado mecánico RGB, switches lineales y conexión USB-C.',
    price: 74.25,
    images: ['https://picsum.photos/seed/p6/800/600'],
    category: 'Electrónica',
    stock: 30,
    rating: 4.3
  },
  {
    id: 'p7',
    title: 'Juego de sábanas premium (King)',
    description: 'Sábanas 100% algodón peinado, 300 hilos, color gris claro.',
    price: 59.0,
    images: ['https://picsum.photos/seed/p7/800/600'],
    category: 'Hogar',
    stock: 18,
    rating: 4.4
  },
  {
    id: 'p8',
    title: 'Auriculares gaming ProGamer',
    description: 'Auriculares con micrófono retráctil, sonido envolvente y almohadillas confort.',
    price: 89.9,
    images: ['https://picsum.photos/seed/p8/800/600'],
    category: 'Gaming',
    stock: 14,
    rating: 4.0
  }
]

export const USERS: User[] = [
  {
    id: 'u1',
    name: 'Usuario Demo',
    email: 'demo@tiendita.com',
    password: 'password123',
    createdAt: '2025-01-01T00:00:00.000Z'
  }
]

export const CATEGORIES: string[] = [...new Set(PRODUCTS.map(p => p.category))]

export const CONVERSATIONS: Conversation[] = []
