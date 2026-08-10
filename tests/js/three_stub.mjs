/* Just enough of three.js to let the animation modules run under node.
 *
 * Nothing here draws. The point is to execute every line of scene setup and
 * every animation frame so that reference errors, temporal dead zones and
 * misspelled properties surface in the test suite instead of in a browser.
 */

class Vec3 {
  constructor(x = 0, y = 0, z = 0) {
    this.set(x, y, z);
  }
  set(x, y, z) {
    this.x = x;
    this.y = y;
    this.z = z;
    return this;
  }
  copy(v) {
    return this.set(v.x, v.y, v.z);
  }
  clone() {
    return new Vec3(this.x, this.y, this.z);
  }
  multiplyScalar(s) {
    return this.set(this.x * s, this.y * s, this.z * s);
  }
  normalize() {
    const n = Math.hypot(this.x, this.y, this.z) || 1;
    return this.multiplyScalar(1 / n);
  }
  project() {
    return this;
  }
  lookAt() {
    return this;
  }
}

class Quaternion {
  setFromUnitVectors(a, b) {
    if (!a || !b || !Number.isFinite(b.x)) {
      throw new Error("setFromUnitVectors got a non-finite vector");
    }
    return this;
  }
}

class Object3D {
  constructor() {
    this.position = new Vec3();
    this.rotation = { x: 0, y: 0, z: 0 };
    this.quaternion = new Quaternion();
    this.up = new Vec3(0, 1, 0);
    this.children = [];
    this.userData = {};
    this.visible = true;
  }
  add(child) {
    this.children.push(child);
    return this;
  }
  remove(child) {
    this.children = this.children.filter((c) => c !== child);
    return this;
  }
  lookAt() {}
}

class Geometry {
  setFromPoints(points) {
    for (const p of points) {
      if (!Number.isFinite(p.x)) throw new Error("non-finite point in geometry");
    }
    this.points = points;
    return this;
  }
  setAttribute(name, attr) {
    this[name] = attr;
    return this;
  }
  dispose() {}
}

class Color {
  constructor(hex = 0xffffff) {
    this.setHex(hex);
  }
  setHex(hex) {
    return this.setRGB(
      ((hex >> 16) & 255) / 255,
      ((hex >> 8) & 255) / 255,
      (hex & 255) / 255,
    );
  }
  setRGB(r, g, b) {
    for (const v of [r, g, b]) {
      if (!Number.isFinite(v)) throw new Error("non-finite colour channel");
    }
    this.r = r;
    this.g = g;
    this.b = b;
    return this;
  }
  setScalar(s) {
    return this.setRGB(s, s, s);
  }
  multiplyScalar(s) {
    return this.setRGB(this.r * s, this.g * s, this.b * s);
  }
}

class Material {
  constructor(opts) {
    Object.assign(this, opts);
    // three turns a hex literal into a Color; the animations rely on that.
    if (typeof this.color === "number") this.color = new Color(this.color);
  }
}

export class Texture {
  constructor(image) {
    this.image = image;
    this.needsUpdate = false;
  }
}
export const NoColorSpace = "";
export const SRGBColorSpace = "srgb";
export const LinearSRGBColorSpace = "srgb-linear";

export const Vector3 = Vec3;
export const Group = Object3D;
export class Mesh extends Object3D {
  constructor(geometry, mat) {
    super();
    this.geometry = geometry;
    this.material = mat;
  }
}
export class Line extends Mesh {}
export class LineSegments extends Mesh {}
export class Points extends Mesh {}
export const BufferGeometry = Geometry;
export class SphereGeometry extends Geometry {}
export class Float32BufferAttribute {
  constructor(array, itemSize) {
    this.array = array;
    this.itemSize = itemSize;
  }
}
export const BufferAttribute = Float32BufferAttribute;
export class ShaderMaterial extends Material {}
export class MeshBasicMaterial extends Material {}
export class LineBasicMaterial extends Material {}
export class PointsMaterial extends Material {}

export class Scene extends Object3D {}

export class PerspectiveCamera extends Object3D {
  constructor(fov, aspect, near, far) {
    super();
    Object.assign(this, { fov, aspect, near, far });
  }
  updateProjectionMatrix() {}
}

export class WebGLRenderer {
  constructor(opts) {
    this.opts = opts;
    this.capabilities = { getMaxAnisotropy: () => 8 };
    this.renders = 0;
  }
  setPixelRatio() {}
  setSize() {}
  setClearColor() {}
  render() {
    this.renders += 1;
  }
  dispose() {}
}
