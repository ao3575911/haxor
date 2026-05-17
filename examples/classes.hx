# Classes and inheritance in Haxor

class Shape:
    fn init(self, name):
        self.name = name

    fn area(self):
        return 0.0

    fn describe(self):
        return f"{self.name} with area {self.area()}"


class Circle(Shape):
    fn init(self, radius):
        self.name = "Circle"
        self.radius = radius

    fn area(self):
        import math
        return math.pi * self.radius * self.radius


class Rectangle(Shape):
    fn init(self, width, height):
        self.name = "Rectangle"
        self.width = width
        self.height = height

    fn area(self):
        return self.width * self.height


class Triangle(Shape):
    fn init(self, base, height):
        self.name = "Triangle"
        self.base = base
        self.height = height

    fn area(self):
        return 0.5 * self.base * self.height


# Polymorphism in action
let shapes = [
    Circle(5),
    Rectangle(4, 6),
    Triangle(3, 8),
]

for shape in shapes:
    print(shape.describe())

# Total area
let total = sum([s.area() for s in shapes])
print(f"\nTotal area: {total}")


# Generic stack data structure
class Stack:
    fn init(self):
        self.data = []

    fn push(self, item):
        self.data += [item]

    fn pop(self):
        if len(self.data) == 0:
            return None
        let last = self.data[len(self.data) - 1]
        self.data = self.data[:len(self.data) - 1]
        return last

    fn peek(self):
        if len(self.data) == 0:
            return None
        return self.data[len(self.data) - 1]

    fn is_empty(self):
        return len(self.data) == 0

    fn size(self):
        return len(self.data)


let stack = Stack()
for i in range(5):
    stack.push(i * 10)

print(f"\nStack size: {stack.size()}")
while not stack.is_empty():
    print(f"  Pop: {stack.pop()}")
