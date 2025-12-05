let navigateFunc = null;

export function setNavigate(func) {
  navigateFunc = func;
}

export function navigate(path) {
  if (navigateFunc) {
    navigateFunc(path);
  } else {
    console.error("navigate() called before setNavigate()");
  }
}
